# Roteiro de Testes - CleanCheck

## Login
- [ ] Admin consegue logar
- [ ] Funcionário consegue logar
- [ ] Usuário inativo não consegue logar
- [ ] Senha errada bloqueia acesso
- [ ] Logout funciona

## Permissões
- [ ] Funcionário não acessa /ambientes
- [ ] Funcionário não acessa /funcionarios
- [ ] Funcionário não acessa /historico
- [ ] Funcionário não acessa /relatorios
- [ ] Admin acessa todas as áreas

## Ambientes
- [ ] Cadastrar ambiente
- [ ] Editar ambiente
- [ ] Desativar ambiente
- [ ] Reativar ambiente
- [ ] Buscar ambiente

## Funcionários
- [ ] Cadastrar funcionário
- [ ] Editar funcionário
- [ ] Desativar funcionário
- [ ] Reativar funcionário
- [ ] Resetar senha

## Checklist
- [ ] Marcar ambiente como limpo
- [ ] Registrar não limpo com observação
- [ ] Registrar sem acesso com observação
- [ ] Filtro pendentes funciona
- [ ] Filtro limpos funciona
- [ ] Filtro problemas funciona
- [ ] Busca funciona
- [ ] Progresso atualiza

## Situação do Dia
- [ ] Mostra status correto
- [ ] Mostra funcionário correto
- [ ] Mostra horário correto
- [ ] Busca funciona

## Histórico e Relatórios
- [ ] Histórico filtra por data
- [ ] PDF gera por período
- [ ] PDF baixa corretamente

## Segurança
- [ ] CSRF bloqueia formulário sem token
- [ ] Acesso manual a rotas admin é bloqueado