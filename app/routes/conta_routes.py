from flask import Blueprint, request, jsonify
from app.controllers import conta_controller

conta_bp = Blueprint('conta_bp', __name__)

@conta_bp.route('/CONTAS', methods=['GET'])
def get_contas():
    return jsonify(conta_controller.listar_contas_ativas()), 200

@conta_bp.route('/CONTAS/<prioridade>', methods=['GET'])
def get_contas_prioridade(prioridade):
    return jsonify(conta_controller.listar_contas_por_prioridade(prioridade)), 200

@conta_bp.route('/CONTAS', methods=['POST'])
def post_conta():
    try:
        conta_controller.criar_conta(request.json)
        return jsonify({'message': 'Conta criada e agendada com sucesso!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@conta_bp.route('/CONTAS/<int:id>', methods=['PUT'])
def put_conta(id):
    conta_controller.atualizar_conta(id, request.json)
    return jsonify({'message': 'Conta atualizada com sucesso!'}), 200

@conta_bp.route('/CONTAS/STATUS/<int:id>', methods=['PUT'])
def put_conta_status(id):
    novo_status = request.json.get('STATUS')
    conta_controller.atualizar_status_conta(id, novo_status)
    return jsonify({'message': 'Status atualizado e processos sincronizados.'}), 200

@conta_bp.route('/CONTAS/<int:id>', methods=['DELETE'])
def delete_conta(id):
    conta_controller.deletar_conta(id)
    return jsonify({'message': 'Conta apagada.'}), 200