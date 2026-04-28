from flask import Blueprint, request, jsonify
from app.controllers import evento_controller

# Criando o Blueprint para as rotas de evento
evento_bp = Blueprint('evento_bp', __name__)

@evento_bp.route('/EVENTO', methods=['GET'])
def get_eventos():
    """Rota para listar todos os eventos."""
    eventos = evento_controller.listar_eventos()
    return jsonify(eventos), 200

@evento_bp.route('/EVENTO', methods=['POST'])
def post_evento():
    """Rota para criar um novo evento."""
    try:
        evento_controller.criar_evento(request.json)
        return jsonify({'message': 'Evento criado, adicionado ao calendário e e-mails agendados com sucesso!'}), 201
    except Exception as e:
        return jsonify({'error': f'Erro ao criar evento: {str(e)}'}), 400

@evento_bp.route('/EVENTO/<int:id>', methods=['PUT'])
def put_evento(id):
    """Rota para atualizar os dados de um evento."""
    try:
        evento_controller.atualizar_evento(id, request.json)
        return jsonify({'message': 'Evento atualizado com sucesso!'}), 200
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar evento: {str(e)}'}), 400

@evento_bp.route('/EVENTO/<int:id>', methods=['DELETE'])
def delete_evento(id):
    """Rota para deletar um evento."""
    try:
        evento_controller.deletar_evento(id)
        return jsonify({'message': 'Evento apagado com sucesso. Alertas cancelados.'}), 200
    except Exception as e:
        return jsonify({'error': f'Erro ao deletar evento: {str(e)}'}), 400