from datetime import datetime, timedelta
from app import db, scheduler
from app.models import Evento
from app.services import enviar_email, get_gcal_service, deletar_evento_gcal, cancelar_alertas
from config import Config

def listar_eventos():
    """Retorna todos os eventos cadastrados."""
    eventos = Evento.query.all()
    return [{
        'IDEVENTO': e.IDEVENTO, 
        'NOMEEVENTO': e.NOMEEVENTO, 
        'TIPO': e.TIPO,
        'DATAEVENTO': str(e.DATAEVENTO),
        'HORARIO': str(e.HORARIO),
        'STATUS': e.STATUS
    } for e in eventos]

def criar_evento(data):
    """Cria um evento, salva no banco, no GCal e agenda os emails."""
    novo_evento = Evento(
        NOMEEVENTO=data['NOMEEVENTO'],
        TIPO=data.get('TIPO'),
        DATAEVENTO=datetime.strptime(data['DATAEVENTO'], '%Y-%m-%d').date(),
        HORARIO=datetime.strptime(data['HORARIO'], '%H:%M:%S').time(),
        STATUS=data.get('STATUS', 'ativo')
    )
    db.session.add(novo_evento)
    db.session.commit()

    # 1. Integração com o Google Calendar
    try:
        service = get_gcal_service()
        # Formata para o padrão aceito pelo Google (RFC3339) com fuso horário de Brasília (-03:00)
        data_hora_str = f"{data['DATAEVENTO']}T{data['HORARIO']}-03:00" 
        
        gcal_event = {
            'summary': f"Evento: {novo_evento.NOMEEVENTO}",
            'start': {'dateTime': data_hora_str},
            'end': {'dateTime': data_hora_str},
        }
        evento_criado = service.events().insert(calendarId='primary', body=gcal_event).execute()
        
        # Salva o ID do Google Calendar no banco
        novo_evento.GCAL_ID = evento_criado['id']
        db.session.commit()
    except Exception as e:
        print(f"Aviso: Erro ao integrar com o Google Calendar: {e}")

    # 2. Agendamento de Emails
    email_dest = data.get('EMAIL_DESTINO', Config.EMAIL_ADDRESS)
    now = datetime.now()
    
    # Data de amanhã (Véspera do evento)
    data_vespera = novo_evento.DATAEVENTO - timedelta(days=1)
    
    # Email 1 dia antes
    run_date_vespera = datetime.combine(data_vespera, datetime.min.time())
    if run_date_vespera > now:
        scheduler.add_job(
            enviar_email, 'date', 
            run_date=run_date_vespera,
            args=[f"Evento Amanhã: {novo_evento.NOMEEVENTO}", email_dest, f"Lembrete! O evento '{novo_evento.NOMEEVENTO}' será amanhã às {novo_evento.HORARIO}."],
            id=f"evento_vespera_{novo_evento.IDEVENTO}"
        )
    
    # Email no dia do Evento (à meia-noite)
    run_date_hoje = datetime.combine(novo_evento.DATAEVENTO, datetime.min.time())
    if run_date_hoje > now:
        scheduler.add_job(
            enviar_email, 'date', 
            run_date=run_date_hoje,
            args=[f"Evento Hoje: {novo_evento.NOMEEVENTO}", email_dest, f"É hoje! Seu evento '{novo_evento.NOMEEVENTO}' acontecerá às {novo_evento.HORARIO}."],
            id=f"evento_hoje_{novo_evento.IDEVENTO}"
        )

    # Email no horário exato do Evento
    run_date_exato = datetime.combine(novo_evento.DATAEVENTO, novo_evento.HORARIO)
    if run_date_exato > now:
        scheduler.add_job(
            enviar_email, 'date', 
            run_date=run_date_exato,
            args=[f"O evento '{novo_evento.NOMEEVENTO}' está começando!", email_dest, f"Atenção: O evento '{novo_evento.NOMEEVENTO}' agendado para as {novo_evento.HORARIO} começou agora."],
            id=f"evento_exato_{novo_evento.IDEVENTO}"
        )

def atualizar_evento(id, data):
    """Atualiza as informações de um evento existente."""
    evento = Evento.query.get_or_404(id)
    
    if 'NOMEEVENTO' in data: evento.NOMEEVENTO = data['NOMEEVENTO']
    if 'TIPO' in data: evento.TIPO = data['TIPO']
    if 'STATUS' in data: evento.STATUS = data['STATUS']
    
    if 'DATAEVENTO' in data: 
        evento.DATAEVENTO = datetime.strptime(data['DATAEVENTO'], '%Y-%m-%d').date()
    if 'HORARIO' in data: 
        evento.HORARIO = datetime.strptime(data['HORARIO'], '%H:%M:%S').time()
    
    db.session.commit()

def deletar_evento(id):
    """Deleta o evento do banco, apaga do GCal e cancela os e-mails agendados."""
    evento = Evento.query.get_or_404(id)
    
    # Limpa integrações e agendamentos
    deletar_evento_gcal(evento.GCAL_ID)
    cancelar_alertas(f"evento_.*_{id}$") # Pega tanto 'evento_vespera_id' quanto 'evento_hoje_id'
    
    db.session.delete(evento)
    db.session.commit()