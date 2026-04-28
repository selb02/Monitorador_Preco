from app import db

class Conta(db.Model):
    __tablename__ = 'conta'
    IDCONTA = db.Column(db.Integer, primary_key=True)
    NOMECONTA = db.Column(db.String(100), nullable=False)
    PRIORIDADE = db.Column(db.String(50))
    TIPO = db.Column(db.String(50))
    PRECO = db.Column(db.Float, nullable=False)
    DATAVENCIMENTO = db.Column(db.Date, nullable=False)
    DATAPAGAMENTO = db.Column(db.Date)
    STATUS = db.Column(db.String(50), default='ativo')
    GCAL_ID = db.Column(db.String(100))

class Evento(db.Model):
    __tablename__ = 'evento'
    IDEVENTO = db.Column(db.Integer, primary_key=True)
    NOMEEVENTO = db.Column(db.String(100), nullable=False)
    TIPO = db.Column(db.String(50))
    DATAEVENTO = db.Column(db.Date, nullable=False)
    HORARIO = db.Column(db.Time, nullable=False)
    STATUS = db.Column(db.String(50), default='ativo')
    GCAL_ID = db.Column(db.String(100))