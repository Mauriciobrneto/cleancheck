from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
from zoneinfo import ZoneInfo
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

from config import Config
from models import db, Usuario, Ambiente, RegistroLimpeza, LogAcao

import io
import csv
import zipfile


app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


def admin_required():
    if current_user.tipo != "admin":
        flash("Acesso negado!", "danger")
        return False

    return True


def agora_brasil():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))


def formatar_status(status):
    status_formatado = {
        "limpo": "Limpo",
        "nao_limpo": "Não limpo",
        "nao_autorizado": "Não autorizado"
    }

    return status_formatado.get(status, status)


def registrar_log(acao):
    log = LogAcao(
        usuario_id=current_user.id,
        acao=acao
    )

    db.session.add(log)


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():

    if request.method == "POST":
        usuario_digitado = request.form.get("usuario").lower()
        senha = request.form.get("senha")

        usuario = Usuario.query.filter_by(usuario=usuario_digitado).first()

        if usuario and usuario.ativo and check_password_hash(usuario.senha, senha):
            login_user(usuario)
            return redirect(url_for("dashboard"))

        flash("Usuário ou senha inválidos!", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():

    if current_user.tipo == "funcionario":
        return render_template("dashboard_funcionario.html")

    total_ambientes = Ambiente.query.filter_by(ativo=True).count()

    limpezas_hoje = RegistroLimpeza.query.filter_by(
        data_registro=date.today(),
        status="limpo"
    ).count()

    problemas = RegistroLimpeza.query.filter(
        RegistroLimpeza.data_registro == date.today(),
        RegistroLimpeza.status.in_([
            "nao_limpo",
            "nao_autorizado"
        ])
    ).count()

    registros_hoje = RegistroLimpeza.query.filter_by(
        data_registro=date.today()
    ).count()

    pendentes = total_ambientes - registros_hoje

    if pendentes < 0:
        pendentes = 0

    return render_template(
        "dashboard.html",
        total_ambientes=total_ambientes,
        limpezas_hoje=limpezas_hoje,
        pendentes=pendentes,
        problemas=problemas,
        data_hoje=date.today().strftime("%d/%m/%Y")
    )


@app.route("/ambientes", methods=["GET", "POST"])
@login_required
def ambientes():

    if not admin_required():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome")
        descricao = request.form.get("descricao")
        frequencia = request.form.get("frequencia")

        novo_ambiente = Ambiente(
            nome=nome,
            descricao=descricao,
            frequencia=frequencia
        )

        db.session.add(novo_ambiente)
        registrar_log(f"Cadastrou o ambiente: {nome}")
        db.session.commit()

        flash("Ambiente cadastrado com sucesso!", "success")

        return redirect(url_for("ambientes"))

    busca = request.args.get("busca", "")

    query = Ambiente.query.filter_by(ativo=True)

    if busca:
        query = query.filter(Ambiente.nome.like(f"%{busca}%"))

    lista_ambientes = query.order_by(Ambiente.nome.asc()).all()

    return render_template(
        "ambientes.html",
        ambientes=lista_ambientes,
        busca=busca
    )


@app.route("/ambientes/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_ambiente(id):

    if not admin_required():
        return redirect(url_for("dashboard"))

    ambiente = Ambiente.query.get_or_404(id)

    if request.method == "POST":
        ambiente.nome = request.form.get("nome")
        ambiente.descricao = request.form.get("descricao")
        ambiente.frequencia = request.form.get("frequencia")

        registrar_log(f"Editou o ambiente: {ambiente.nome}")
        db.session.commit()

        flash("Ambiente atualizado com sucesso!", "success")

        return redirect(url_for("ambientes"))

    return render_template(
        "editar_ambiente.html",
        ambiente=ambiente
    )


@app.route("/ambientes/<int:id>/desativar", methods=["POST"])
@login_required
def desativar_ambiente(id):

    if not admin_required():
        return redirect(url_for("dashboard"))

    ambiente = Ambiente.query.get_or_404(id)
    ambiente.ativo = False

    registrar_log(f"Desativou o ambiente: {ambiente.nome}")

    db.session.commit()

    flash("Ambiente desativado com sucesso!", "warning")

    return redirect(url_for("ambientes"))


@app.route("/ambientes/inativos")
@login_required
def ambientes_inativos():

    if not admin_required():
        return redirect(url_for("dashboard"))

    ambientes = Ambiente.query.filter_by(ativo=False).order_by(
        Ambiente.nome.asc()
    ).all()

    return render_template(
        "ambientes_inativos.html",
        ambientes=ambientes
    )


@app.route("/ambientes/<int:id>/reativar", methods=["POST"])
@login_required
def reativar_ambiente(id):

    if not admin_required():
        return redirect(url_for("dashboard"))

    ambiente = Ambiente.query.get_or_404(id)
    ambiente.ativo = True

    registrar_log(f"Reativou o ambiente: {ambiente.nome}")

    db.session.commit()

    flash("Ambiente reativado com sucesso!", "success")

    return redirect(url_for("ambientes_inativos"))


@app.route("/funcionarios", methods=["GET", "POST"])
@login_required
def funcionarios():

    if not admin_required():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome")
        usuario = request.form.get("usuario").lower()
        senha = request.form.get("senha")
        tipo = request.form.get("tipo", "funcionario")

        email = f"{usuario}@cleancheck.local"

        funcionario = Usuario(
            nome=nome,
            usuario=usuario,
            email=email,
            senha=generate_password_hash(senha),
            tipo=tipo,
            ativo=True
        )

        db.session.add(funcionario)
        registrar_log(f"Cadastrou o usuário: {nome} como {tipo}")
        db.session.commit()

        flash("Usuário cadastrado com sucesso!", "success")

        return redirect(url_for("funcionarios"))

    lista_funcionarios = Usuario.query.filter_by(
        ativo=True
    ).order_by(
        Usuario.nome.asc()
    ).all()

    return render_template(
        "funcionarios.html",
        funcionarios=lista_funcionarios
    )


@app.route("/funcionarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_funcionario(id):

    if not admin_required():
        return redirect(url_for("dashboard"))

    funcionario = Usuario.query.get_or_404(id)

    if request.method == "POST":
        novo_tipo = request.form.get("tipo", "funcionario")

        admins_ativos = Usuario.query.filter_by(
            tipo="admin",
            ativo=True
        ).count()

        if funcionario.tipo == "admin" and novo_tipo != "admin" and admins_ativos <= 1:
            flash(
                "Não é possível remover o acesso do último administrador.",
                "danger"
            )

            return redirect(url_for("funcionarios"))

        funcionario.nome = request.form.get("nome")
        funcionario.usuario = request.form.get("usuario").lower()
        funcionario.tipo = novo_tipo

        registrar_log(f"Editou o usuário: {funcionario.nome}")

        db.session.commit()

        flash("Usuário atualizado com sucesso!", "success")

        return redirect(url_for("funcionarios"))

    return render_template(
        "editar_funcionario.html",
        funcionario=funcionario
    )


@app.route("/funcionarios/<int:id>/desativar", methods=["POST"])
@login_required
def desativar_funcionario(id):

    if not admin_required():
        return redirect(url_for("dashboard"))

    funcionario = Usuario.query.get_or_404(id)

    admins_ativos = Usuario.query.filter_by(
        tipo="admin",
        ativo=True
    ).count()

    if funcionario.tipo == "admin" and admins_ativos <= 1:
        flash(
            "Não é possível desativar o último administrador.",
            "danger"
        )

        return redirect(url_for("funcionarios"))

    funcionario.ativo = False

    registrar_log(f"Desativou o usuário: {funcionario.nome}")

    db.session.commit()

    flash("Usuário desativado com sucesso!", "warning")

    return redirect(url_for("funcionarios"))


@app.route("/funcionarios/inativos")
@login_required
def funcionarios_inativos():

    if not admin_required():
        return redirect(url_for("dashboard"))

    funcionarios = Usuario.query.filter_by(
        ativo=False
    ).order_by(
        Usuario.nome.asc()
    ).all()

    return render_template(
        "funcionarios_inativos.html",
        funcionarios=funcionarios
    )


@app.route("/funcionarios/<int:id>/reativar", methods=["POST"])
@login_required
def reativar_funcionario(id):

    if not admin_required():
        return redirect(url_for("dashboard"))

    funcionario = Usuario.query.get_or_404(id)
    funcionario.ativo = True

    registrar_log(f"Reativou o usuário: {funcionario.nome}")

    db.session.commit()

    flash("Usuário reativado com sucesso!", "success")

    return redirect(url_for("funcionarios_inativos"))


@app.route("/funcionarios/<int:id>/resetar-senha", methods=["GET", "POST"])
@login_required
def resetar_senha(id):

    if not admin_required():
        return redirect(url_for("dashboard"))

    funcionario = Usuario.query.get_or_404(id)

    if request.method == "POST":
        nova_senha = request.form.get("senha")

        funcionario.senha = generate_password_hash(nova_senha)

        registrar_log(f"Resetou a senha do usuário: {funcionario.nome}")

        db.session.commit()

        flash("Senha resetada com sucesso!", "success")

        return redirect(url_for("funcionarios"))

    return render_template(
        "resetar_senha.html",
        funcionario=funcionario
    )


@app.route("/minha-conta", methods=["GET", "POST"])
@login_required
def minha_conta():

    if request.method == "POST":
        senha_atual = request.form.get("senha_atual")
        nova_senha = request.form.get("nova_senha")

        if not check_password_hash(current_user.senha, senha_atual):
            flash("Senha atual incorreta!", "danger")
            return redirect(url_for("minha_conta"))

        current_user.senha = generate_password_hash(nova_senha)

        registrar_log("Alterou a própria senha")

        db.session.commit()

        flash("Senha alterada com sucesso!", "success")

        return redirect(url_for("dashboard"))

    return render_template("minha_conta.html")


@app.route("/checklist", methods=["GET", "POST"])
@login_required
def checklist():

    if request.method == "POST":
        ambiente_id = request.form.get("ambiente_id")
        status = request.form.get("status")
        observacao = request.form.get("observacao", "")
        acao = request.form.get("acao")

        if acao == "limpo":
            status = "limpo"

        elif acao == "nao_limpo":
            status = "nao_limpo"

        elif acao == "nao_autorizado":
            status = "nao_autorizado"

        registro_existente = RegistroLimpeza.query.filter_by(
            ambiente_id=ambiente_id,
            data_registro=date.today()
        ).first()

        if registro_existente:
            registro_existente.status = status
            registro_existente.observacao = observacao
            registro_existente.usuario_id = current_user.id
            registro_existente.hora_registro = agora_brasil().time()

            registrar_log(
                f"Atualizou checklist do ambiente ID {ambiente_id} para {status}"
            )

        else:
            novo_registro = RegistroLimpeza(
                ambiente_id=ambiente_id,
                usuario_id=current_user.id,
                status=status,
                observacao=observacao,
                data_registro=date.today(),
                hora_registro=agora_brasil().time()
            )

            db.session.add(novo_registro)

            registrar_log(
                f"Registrou checklist do ambiente ID {ambiente_id} como {status}"
            )

        db.session.commit()

        flash("Registro salvo com sucesso!", "success")

        return redirect(url_for("checklist"))

    busca = request.args.get("busca", "")
    filtro = request.args.get("filtro", "todos")

    query = Ambiente.query.filter_by(ativo=True)

    if busca:
        query = query.filter(Ambiente.nome.like(f"%{busca}%"))

    ambientes = query.order_by(Ambiente.nome.asc()).all()

    situacao = []

    for ambiente in ambientes:
        registro = RegistroLimpeza.query.filter_by(
            ambiente_id=ambiente.id,
            data_registro=date.today()
        ).order_by(
            RegistroLimpeza.hora_registro.desc()
        ).first()

        situacao.append({
            "ambiente": ambiente,
            "registro": registro
        })

    total_ambientes = len(situacao)

    situacao.sort(
        key=lambda item: (
            item["registro"] is not None,
            item["ambiente"].nome
        )
    )

    if filtro == "pendentes":
        situacao = [
            item for item in situacao
            if not item["registro"]
        ]

    elif filtro == "limpos":
        situacao = [
            item for item in situacao
            if item["registro"] and item["registro"].status == "limpo"
        ]

    elif filtro == "problemas":
        situacao = [
            item for item in situacao
            if item["registro"] and item["registro"].status in [
                "nao_limpo",
                "nao_autorizado",
                "sem_acesso"
            ]
        ]

    concluidos = 0

    for item in situacao:
        if item["registro"]:
            concluidos += 1

    porcentagem = 0

    if total_ambientes > 0:
        porcentagem = int((concluidos / total_ambientes) * 100)

    return render_template(
        "checklist.html",
        situacao=situacao,
        busca=busca,
        filtro=filtro,
        total_ambientes=total_ambientes,
        concluidos=concluidos,
        porcentagem=porcentagem
    )


@app.route("/situacao-dia")
@login_required
def situacao_dia():

    busca = request.args.get("busca", "")

    query = Ambiente.query.filter_by(ativo=True)

    if busca:
        query = query.filter(Ambiente.nome.like(f"%{busca}%"))

    ambientes = query.order_by(
        Ambiente.nome.asc()
    ).all()

    situacao = []

    for ambiente in ambientes:
        registro = RegistroLimpeza.query.filter_by(
            ambiente_id=ambiente.id,
            data_registro=date.today()
        ).order_by(
            RegistroLimpeza.hora_registro.desc()
        ).first()

        usuario = None

        if registro:
            usuario = db.session.get(Usuario, registro.usuario_id)

        situacao.append({
            "ambiente": ambiente,
            "registro": registro,
            "usuario": usuario
        })

    return render_template(
        "situacao_dia.html",
        situacao=situacao,
        busca=busca
    )


@app.route("/historico")
@login_required
def historico():

    if not admin_required():
        return redirect(url_for("dashboard"))

    data_filtro = request.args.get("data")

    if data_filtro:
        data_busca = datetime.strptime(data_filtro, "%Y-%m-%d").date()
    else:
        data_busca = date.today()
        data_filtro = data_busca.strftime("%Y-%m-%d")

    registros = RegistroLimpeza.query.filter_by(
        data_registro=data_busca
    ).order_by(
        RegistroLimpeza.hora_registro.desc()
    ).all()

    return render_template(
        "historico.html",
        registros=registros,
        data_filtro=data_filtro
    )


@app.route("/relatorios")
@login_required
def relatorios():

    if not admin_required():
        return redirect(url_for("dashboard"))

    return render_template("relatorios.html")


@app.route("/relatorio-pdf")
@login_required
def relatorio_pdf():

    if not admin_required():
        return redirect(url_for("dashboard"))

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    if data_inicio and data_fim:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
    else:
        inicio = date.today()
        fim = date.today()

    registros = RegistroLimpeza.query.filter(
        RegistroLimpeza.data_registro >= inicio,
        RegistroLimpeza.data_registro <= fim
    ).order_by(
        RegistroLimpeza.data_registro.asc(),
        RegistroLimpeza.hora_registro.asc()
    ).all()

    os.makedirs("relatorios", exist_ok=True)

    nome_arquivo = f"relatorio_limpeza_{inicio}_a_{fim}.pdf"
    caminho_pdf = os.path.join("relatorios", nome_arquivo)

    pdf = canvas.Canvas(caminho_pdf, pagesize=A4)
    largura, altura = A4
    y = altura - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Relatório de Limpeza - CleanCheck")

    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        50,
        y,
        f"Período: {inicio.strftime('%d/%m/%Y')} até {fim.strftime('%d/%m/%Y')}"
    )

    y -= 40

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Data")
    pdf.drawString(115, y, "Hora")
    pdf.drawString(170, y, "Ambiente")
    pdf.drawString(310, y, "Status")
    pdf.drawString(420, y, "Responsável")

    y -= 15
    pdf.setFont("Helvetica", 9)

    if registros:
        for registro in registros:

            if y < 80:
                pdf.showPage()
                y = altura - 50
                pdf.setFont("Helvetica", 9)

            pdf.drawString(50, y, registro.data_registro.strftime("%d/%m/%Y"))
            pdf.drawString(115, y, registro.hora_registro.strftime("%H:%M"))
            pdf.drawString(170, y, registro.ambiente.nome[:22])
            pdf.drawString(310, y, formatar_status(registro.status))
            pdf.drawString(420, y, registro.usuario.nome[:18])

            y -= 15

            if registro.observacao:
                pdf.setFont("Helvetica-Oblique", 8)
                pdf.drawString(170, y, f"Obs: {registro.observacao[:80]}")
                pdf.setFont("Helvetica", 9)
                y -= 18

            y -= 8
    else:
        pdf.drawString(50, y, "Nenhum registro encontrado para este período.")

    pdf.save()

    return send_file(caminho_pdf, as_attachment=True)


@app.route("/logs")
@login_required
def logs():

    if not admin_required():
        return redirect(url_for("dashboard"))

    logs = LogAcao.query.order_by(
        LogAcao.criado_em.desc()
    ).all()

    return render_template(
        "logs.html",
        logs=logs
    )


@app.errorhandler(429)
def ratelimit_handler(e):
    flash(
        "Muitas tentativas de login. Aguarde 1 minuto e tente novamente.",
        "danger"
    )

    return redirect(url_for("login"))


with app.app_context():
    db.create_all()

    admin = Usuario.query.filter_by(usuario="admin").first()

    if not admin:
        admin = Usuario(
            nome="Administrador",
            usuario="admin",
            email="admin@cleancheck.com",
            senha=generate_password_hash("123456"),
            tipo="admin",
            ativo=True
        )

        db.session.add(admin)
        db.session.commit()

        print("Administrador criado com sucesso!")

@app.route("/backup")
@login_required
def backup():

    if not admin_required():
        return redirect(url_for("dashboard"))

    memoria = io.BytesIO()

    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zip_file:

        def adicionar_csv(nome_arquivo, cabecalho, linhas):
            arquivo = io.StringIO()
            escritor = csv.writer(arquivo, delimiter=";")

            escritor.writerow(cabecalho)

            for linha in linhas:
                escritor.writerow(linha)

            zip_file.writestr(nome_arquivo, arquivo.getvalue())

        adicionar_csv(
            "usuarios.csv",
            ["id", "nome", "usuario", "email", "tipo", "ativo"],
            [
                [u.id, u.nome, u.usuario, u.email, u.tipo, u.ativo]
                for u in Usuario.query.all()
            ]
        )

        adicionar_csv(
            "ambientes.csv",
            ["id", "nome", "descricao", "frequencia", "ativo"],
            [
                [a.id, a.nome, a.descricao, a.frequencia, a.ativo]
                for a in Ambiente.query.all()
            ]
        )

        adicionar_csv(
            "registros_limpeza.csv",
            ["id", "ambiente_id", "usuario_id", "status", "observacao", "data", "hora"],
            [
                [
                    r.id,
                    r.ambiente_id,
                    r.usuario_id,
                    r.status,
                    r.observacao,
                    r.data_registro,
                    r.hora_registro
                ]
                for r in RegistroLimpeza.query.all()
            ]
        )

        adicionar_csv(
            "logs_acoes.csv",
            ["id", "usuario_id", "acao", "criado_em"],
            [
                [l.id, l.usuario_id, l.acao, l.criado_em]
                for l in LogAcao.query.all()
            ]
        )

    memoria.seek(0)

    nome_backup = f"backup_cleancheck_{agora_brasil().strftime('%Y-%m-%d_%H-%M')}.zip"

    registrar_log("Gerou backup do sistema")
    db.session.commit()

    return send_file(
        memoria,
        as_attachment=True,
        download_name=nome_backup,
        mimetype="application/zip"
    )


if __name__ == "__main__":
    app.run(debug=True)