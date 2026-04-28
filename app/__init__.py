from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from flask_cors import CORS
from config import Config

# Instâncias globais
db = SQLAlchemy()
scheduler = BackgroundScheduler()

def create_app():
    app = Flask(__name__)
    CORS(app) # Habilita CORS para todas as rotas
    app.config.from_object(Config)

    db.init_app(app)
    
    # Configurar o scheduler para usar o banco de dados (persiste os agendamentos)
    # Adicionamos engine_options para evitar que o Render derrube a conexão por inatividade
    jobstores = {
        'default': SQLAlchemyJobStore(
            url=Config.SQLALCHEMY_DATABASE_URI,
            engine_options={'pool_pre_ping': True, 'pool_recycle': 280}
        )
    }
    # Substituir os agendamentos existentes (se houver atualização no código) e definir timezone
    scheduler.configure(jobstores=jobstores)
    
    if not scheduler.running:
        scheduler.start()

    # Registro das Rotas (Blueprints)
    from app.routes.conta_routes import conta_bp
    from app.routes.evento_routes import evento_bp
    app.register_blueprint(conta_bp)
    app.register_blueprint(evento_bp)

    with app.app_context():
        db.create_all()

    return app