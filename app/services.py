import os
import smtplib
import re
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import Config
from app import scheduler

def enviar_email(assunto, destinatario, corpo):
    try:
        msg = EmailMessage()
        msg['Subject'] = assunto
        msg['From'] = Config.EMAIL_ADDRESS
        msg['To'] = destinatario
        msg.set_content(corpo)
        
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Erro ao enviar email: {e}")

def get_gcal_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', Config.SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', Config.SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def deletar_evento_gcal(gcal_id):
    if not gcal_id: return
    try:
        service = get_gcal_service()
        service.events().delete(calendarId='primary', eventId=gcal_id).execute()
    except Exception as e:
        print(f"Erro ao deletar do Google Calendar: {e}")

def cancelar_alertas(padrao_id):
    try:
        jobs = scheduler.get_jobs()
        for job in jobs:
            if re.search(padrao_id, str(job.id)):
                scheduler.remove_job(job.id)
    except Exception as e:
        print(f"Erro ao cancelar alertas: {e}")