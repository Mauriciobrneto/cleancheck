from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)

    tipo = db.Column(
        db.Enum("admin", "funcionario"),
        default="funcionario",
        nullable=False
    )

    ativo = db.Column(db.Boolean, default=True)

    registros = db.relationship(
        "RegistroLimpeza",
        back_populates="usuario"
    )


class Ambiente(db.Model):
    __tablename__ = "ambientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)

    frequencia = db.Column(
        db.Enum("diaria", "semanal", "quinzenal", "mensal"),
        default="diaria",
        nullable=False
    )

    ativo = db.Column(db.Boolean, default=True)

    registros = db.relationship(
        "RegistroLimpeza",
        back_populates="ambiente"
    )


class RegistroLimpeza(db.Model):
    __tablename__ = "registros_limpeza"

    id = db.Column(db.Integer, primary_key=True)

    ambiente_id = db.Column(
        db.Integer,
        db.ForeignKey("ambientes.id"),
        nullable=False
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    status = db.Column(
        db.Enum(
            "limpo",
            "nao_limpo",
            "nao_autorizado",
            "sem_acesso",
            "nao_necessario"
        ),
        nullable=False
    )

    observacao = db.Column(db.Text)
    data_registro = db.Column(db.Date, nullable=False)
    hora_registro = db.Column(db.Time, nullable=False)

    criado_em = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    ambiente = db.relationship(
        "Ambiente",
        back_populates="registros"
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="registros"
    )

class LogAcao(db.Model):
    __tablename__ = "logs_acoes"

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    acao = db.Column(db.String(255), nullable=False)

    criado_em = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    usuario = db.relationship("Usuario")