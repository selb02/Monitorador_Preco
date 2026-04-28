from datetime import datetime, timedelta
from app import db, scheduler
from app.models import Conta
from app.services import enviar_email, get_gcal_service, deletar_evento_gcal, cancelar_alertas
from config import Config

def listar_contas_ativas():
    contas = Conta.query.filter_by(STATUS='ativo').all()
    return [{'IDCONTA': c.IDCONTA, 'NOMECONTA': c.NOMECONTA, 'PRECO': c.PRECO, 'DATAVENCIMENTO': str(c.DATAVENCIMENTO), 'STATUS': c.STATUS} for c in contas]

def listar_contas_por_prioridade(prioridade):
    contas = Conta.query.filter_by(PRIORIDADE=prioridade).all()
    return [{'IDCONTA': c.IDCONTA, 'NOMECONTA': c.NOMECONTA, 'PRIORIDADE': c.PRIORIDADE, 'PRECO': c.PRECO, 'DATAVENCIMENTO': str(c.DATAVENCIMENTO)} for c in contas]

def criar_conta(data):
    nova_conta = Conta(
        NOMECONTA=data['NOMECONTA'],
        PRIORIDADE=data.get('PRIORIDADE'),
        TIPO=data.get('TIPO'),
        PRECO=data['PRECO'],
        DATAVENCIMENTO=datetime.strptime(data['DATAVENCIMENTO'], '%Y-%m-%d').date(),
        DATAPAGAMENTO=datetime.strptime(data['DATAPAGAMENTO'], '%Y-%m-%d').date() if data.get('DATAPAGAMENTO') else None,
        STATUS=data.get('STATUS', 'ativo')
    )
    db.session.add(nova_conta)
    db.session.commit()

    # Google Calendar
    service = get_gcal_service()
    gcal_event = {
        'summary': f"Vencimento: {nova_conta.NOMECONTA}",
        'start': {'date': str(nova_conta.DATAVENCIMENTO)},
        'end': {'date': str(nova_conta.DATAVENCIMENTO)},
    }
    evento_criado = service.events().insert(calendarId='primary', body=gcal_event).execute()
    nova_conta.GCAL_ID = evento_criado['id']
    db.session.commit()

    # Agendamento de Emails
    email_dest = data.get('EMAIL_DESTINO', Config.EMAIL_ADDRESS)
    now = datetime.now()
    
    if nova_conta.DATAPAGAMENTO:
        run_date_pag = datetime.combine(nova_conta.DATAPAGAMENTO, datetime.min.time())
        if run_date_pag > now:
            scheduler.add_job(
                enviar_email, 'date', run_date=run_date_pag,
                args=[f"Pagar hoje: {nova_conta.NOMECONTA}", email_dest, f"Conta: {nova_conta.NOMECONTA} | R${nova_conta.PRECO}"],
                id=f"conta_pag_{nova_conta.IDCONTA}"
            )
        
    data_vespera_venc = nova_conta.DATAVENCIMENTO - timedelta(days=1)
    run_date_vespera = datetime.combine(data_vespera_venc, datetime.min.time())
    if run_date_vespera > now:
        scheduler.add_job(
            enviar_email, 'date', run_date=run_date_vespera,
            args=[f"Amanhã vence: {nova_conta.NOMECONTA}", email_dest, f"Atenção, vence amanhã: R${nova_conta.PRECO}"],
            id=f"conta_venc_vespera_{nova_conta.IDCONTA}"
        )
    
    run_date_venc = datetime.combine(nova_conta.DATAVENCIMENTO, datetime.min.time())
    if run_date_venc > now:
        scheduler.add_job(
            enviar_email, 'date', run_date=run_date_venc,
            args=[f"VENCE HOJE: {nova_conta.NOMECONTA}", email_dest, f"Vencimento hoje: R${nova_conta.PRECO}"],
            id=f"conta_venc_{nova_conta.IDCONTA}"
        )

def atualizar_conta(id, data):
    conta = Conta.query.get_or_404(id)
    if 'NOMECONTA' in data: conta.NOMECONTA = data['NOMECONTA']
    if 'PRIORIDADE' in data: conta.PRIORIDADE = data['PRIORIDADE']
    if 'TIPO' in data: conta.TIPO = data['TIPO']
    if 'PRECO' in data: conta.PRECO = data['PRECO']
    if 'DATAVENCIMENTO' in data: conta.DATAVENCIMENTO = datetime.strptime(data['DATAVENCIMENTO'], '%Y-%m-%d').date()
    if 'DATAPAGAMENTO' in data: conta.DATAPAGAMENTO = datetime.strptime(data['DATAPAGAMENTO'], '%Y-%m-%d').date()
    db.session.commit()

def atualizar_status_conta(id, novo_status):
    conta = Conta.query.get_or_404(id)
    conta.STATUS = novo_status
    db.session.commit()

    if novo_status.lower() in ['pago', 'finalizado', 'inativo']:
        deletar_evento_gcal(conta.GCAL_ID)
        cancelar_alertas(f"conta_.*_{id}$")
        conta.GCAL_ID = None
        db.session.commit()

def deletar_conta(id):
    conta = Conta.query.get_or_404(id)
    deletar_evento_gcal(conta.GCAL_ID)
    cancelar_alertas(f"conta_.*_{id}$")
    db.session.delete(conta)
    db.session.commit()