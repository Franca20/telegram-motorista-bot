"""
Gerenciador de autenticação de usuários do bot Telegram.
Salva usuários autenticados e controla acesso aos dados.
"""
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class GerenciadorUsuarios:
    def __init__(self, arquivo_usuarios='usuarios.json'):
        self.arquivo = Path(arquivo_usuarios)
        self.usuarios = {}
        self._carregar_usuarios()
    
    def _carregar_usuarios(self):
        """Carrega usuários do arquivo JSON."""
        if self.arquivo.exists():
            try:
                with open(self.arquivo, 'r') as f:
                    self.usuarios = json.load(f)
                logger.info(f"Carregados {len(self.usuarios)} usuários do arquivo")
            except Exception as e:
                logger.error(f"Erro ao carregar usuários: {e}")
                self.usuarios = {}
        else:
            logger.info("Arquivo de usuários não encontrado. Criando novo.")
            self.usuarios = {}
    
    def _salvar_usuarios(self):
        """Salva usuários no arquivo JSON."""
        try:
            with open(self.arquivo, 'w') as f:
                json.dump(self.usuarios, f, indent=2)
            logger.info(f"Usuários salvos no arquivo: {len(self.usuarios)} usuários")
        except Exception as e:
            logger.error(f"Erro ao salvar usuários: {e}")
    
    def autenticar(self, chat_id: int, senha: str) -> dict:
        """Autentica um usuário com senha.
        
        Retorna:
            dict: {'status': 'sucesso'|'erro', 'mensagem': str}
        """
        chat_id_str = str(chat_id)
        
        # Verifica se usuário já está autenticado
        if chat_id_str in self.usuarios:
            return {
                'status': 'aviso',
                'mensagem': 'Você já está autenticado!'
            }
        
        # Verifica se a senha está correta (carregada do .env no main.py)
        # A senha será validada no main.py
        # Aqui apenas registramos o usuário
        self.usuarios[chat_id_str] = {
            'chat_id': chat_id,
            'data_autenticacao': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'motoristas': []  # Lista de LH dos motoristas que este usuário criou
        }
        self._salvar_usuarios()
        
        return {
            'status': 'sucesso',
            'mensagem': 'Autenticação realizada com sucesso! Bem-vindo ao sistema.'
        }
    
    def esta_autenticado(self, chat_id: int) -> bool:
        """Verifica se um usuário está autenticado."""
        return str(chat_id) in self.usuarios
    
    def adicionar_motorista(self, chat_id: int, lh: str) -> bool:
        """Registra que um usuário adicionou um motorista."""
        chat_id_str = str(chat_id)
        if chat_id_str in self.usuarios:
            if lh not in self.usuarios[chat_id_str]['motoristas']:
                self.usuarios[chat_id_str]['motoristas'].append(lh)
                self._salvar_usuarios()
                return True
        return False
    
    def remover_motorista(self, chat_id: int, lh: str) -> bool:
        """Remove um motorista da lista do usuário."""
        chat_id_str = str(chat_id)
        if chat_id_str in self.usuarios and lh in self.usuarios[chat_id_str]['motoristas']:
            self.usuarios[chat_id_str]['motoristas'].remove(lh)
            self._salvar_usuarios()
            return True
        return False
    
    def pode_editar_motorista(self, chat_id: int, lh: str) -> bool:
        """Verifica se um usuário pode editar um motorista (se foi ele que criou)."""
        chat_id_str = str(chat_id)
        if chat_id_str in self.usuarios:
            return lh in self.usuarios[chat_id_str]['motoristas']
        return False
    
    def obter_motoristas_usuario(self, chat_id: int) -> list:
        """Retorna lista de LH dos motoristas criados pelo usuário."""
        chat_id_str = str(chat_id)
        if chat_id_str in self.usuarios:
            return self.usuarios[chat_id_str]['motoristas']
        return []
