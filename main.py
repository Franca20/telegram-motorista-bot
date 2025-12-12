from dotenv import load_dotenv
from pathlib import Path
import requests
import os
from estrutura import RoboBolsao
from planilha_fechamento import PlanilhaFechamento
from gerenciador_usuarios import GerenciadorUsuarios
import threading
import logging
import time
from typing import Optional, Dict, Any

# Configurar logging para debug
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotTelegram:
    def __init__(self, bot_bolsao, token=None, texto=None, chat_id=None, clear_on_start=True, keep_last_n=0, 
                 max_retries=5, retry_delay=5):
        self.bot_bolsao = bot_bolsao
        self.texto = texto
        self.chat_id = chat_id
        self.token = token
        self.senha_planilha = None  # Será carregada do .env
        self.senha_autenticacao = None  # Será carregada do .env
        self.link_base = None
        self.clear_on_start = clear_on_start
        self.keep_last_n = keep_last_n
        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # Request timeout
        self.timeout = 30
        # Planilha de fechamento
        self.planilha = PlanilhaFechamento(diretorio='.')
        # Gerenciador de usuários
        self.gerenciador_usuarios = GerenciadorUsuarios('usuarios.json')

    def get_updates_com_retry(self) -> Optional[Dict[str, Any]]:
        """Faz requisição com retry automático em caso de falha de conexão."""
        url = f"{self.link_base}getUpdates"
        for tentativa in range(1, self.max_retries + 1):
            try:
                response = requests.post(url, timeout=self.timeout)
                response.raise_for_status()
                dados = response.json()
                if dados.get('ok'):
                    return dados
                else:
                    erro = dados.get('description', 'Erro desconhecido')
                    logger.error(f"Erro da API: {erro}")
                    return None
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout na tentativa {tentativa}/{self.max_retries}")
                if tentativa < self.max_retries:
                    time.sleep(self.retry_delay)
                continue
            except requests.exceptions.ConnectionError:
                logger.warning(f"Erro de conexão na tentativa {tentativa}/{self.max_retries}")
                if tentativa < self.max_retries:
                    time.sleep(self.retry_delay)
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro na requisição: {e}")
                if tentativa < self.max_retries:
                    time.sleep(self.retry_delay)
                continue
            except ValueError as e:
                logger.error(f"Erro ao decodificar JSON: {e}")
                return None
        
        logger.error(f"Falha após {self.max_retries} tentativas")
        return None

    def rodarbot(self):
        ultimo_update_id = None
        logger.info("Bot iniciando...")

        # Optionally clear the backlog of updates on startup so old messages are not processed
        if self.clear_on_start:
            try:
                self.clear_history(keep_last_n=self.keep_last_n)
                logger.info("Histórico limpo com sucesso")
            except Exception as e:
                logger.warning(f"Falha ao limpar histórico no início: {e}")

        logger.info("Bot pronto para receber mensagens")
        
        while True:
            try:
                # ensure link_base is formatted with token
                if not self.link_base and self.token:
                    self.link_base = f"https://api.telegram.org/bot{self.token}/"

                # Fazer requisição com retry
                dados = self.get_updates_com_retry()
                if not dados:
                    logger.warning("Nenhum dado retornado, aguardando antes de tentar novamente...")
                    time.sleep(self.retry_delay)
                    continue
                
                for update in dados.get('result', []):
                    try:
                        update_id = update.get('update_id')
                        if ultimo_update_id is None or update_id > ultimo_update_id:
                            if 'message' in update:
                                self._processar_mensagem(update, chat_id=update['message']['chat'].get('id'))
                                ultimo_update_id = update_id
                    except (KeyError, TypeError) as e:
                        logger.error(f"Erro ao processar update {update_id}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Erro inesperado ao processar update: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Erro crítico no loop principal: {e}", exc_info=True)
                logger.info(f"Aguardando {self.retry_delay} segundos antes de reconectar...")
                time.sleep(self.retry_delay)
                continue

    def _processar_mensagem(self, update: Dict[str, Any], chat_id: int):
        """Processa uma mensagem de forma isolada com tratamento de erro."""
        try:
            msg = update['message']
            nome = msg['from'].get('first_name', 'Desconhecido')
            mensagem = msg.get('text', '')
            
            logger.info(f"Nova mensagem de {nome} ({chat_id}): {mensagem}")

            # Comando login (não requer autenticação)
            if mensagem.startswith('/login'):
                senha_fornecida = mensagem.replace('/login', '').strip()
                if not senha_fornecida:
                    self.send_message(chat_id, "[AVISO] Use: /login SENHA")
                    return
                
                if senha_fornecida != self.senha_autenticacao:
                    logger.warning(f"Tentativa de login com senha incorreta do usuário {chat_id}")
                    self.send_message(chat_id, "[ERRO] Senha incorreta! Autenticação falhou.")
                    return
                
                resultado = self.gerenciador_usuarios.autenticar(chat_id, senha_fornecida)
                if resultado['status'] == 'sucesso':
                    self.send_message(chat_id, f"[OK] {resultado['mensagem']}\n\nDigite /help para ver os comandos disponíveis.")
                    logger.info(f"Usuário {chat_id} ({nome}) autenticado com sucesso")
                else:
                    self.send_message(chat_id, f"[AVISO] {resultado['mensagem']}")
                return

            # Verifica se usuário está autenticado para os outros comandos
            if not self.gerenciador_usuarios.esta_autenticado(chat_id):
                self.send_message(chat_id, "[ERRO] Você não está autenticado!\nUse: /login SENHA")
                logger.warning(f"Acesso negado para usuário não autenticado {chat_id}: {mensagem}")
                return

            # Comandos que requerem autenticação
            if mensagem == '/help' or mensagem.startswith('/help'):
                self._enviar_ajuda(chat_id)
                return
            
            if mensagem.startswith('/placa'):
                placa = mensagem.replace('/placa', '').strip()
                if placa:
                    threading.Thread(
                        target=self.pesquisa_placa_async, 
                        args=(chat_id, placa), 
                        daemon=True
                    ).start()
                else:
                    self.send_message(chat_id, "[ERRO] Uso: /placa ABC1234")
                    
            elif mensagem.startswith('/lh'):
                lh = mensagem.replace('/lh', '').strip()
                if lh:
                    threading.Thread(
                        target=self.pesquisa_lh_async, 
                        args=(chat_id, lh), 
                        daemon=True
                    ).start()
                else:
                    self.send_message(chat_id, "[ERRO] Uso: /lh 1234567890123")

            elif mensagem.startswith('/remove'):
                dado_para_remover = mensagem.replace('/remove', '').strip()
                if dado_para_remover:
                    # Valida se o usuário pode remover este motorista
                    if not self.gerenciador_usuarios.pode_editar_motorista(chat_id, dado_para_remover):
                        self.send_message(chat_id, "[ERRO] Você não tem permissão para remover este motorista!\nVocê só pode remover motoristas que criou.")
                        logger.warning(f"Tentativa de remover motorista sem permissão - Usuário: {chat_id}, Motorista: {dado_para_remover}")
                        return
                    
                    try:
                        resultado = self.bot_bolsao.remover_motorista(dado_para_remover)
                        if resultado['status'] == 'sucesso':
                            self.send_message(chat_id, f"[OK] {resultado['mensagem']}")
                            self.gerenciador_usuarios.remover_motorista(chat_id, dado_para_remover)
                            logger.info(f"Motorista removido por {chat_id}: {dado_para_remover}")
                        else:
                            self.send_message(chat_id, f"[ERRO] {resultado['mensagem']}")
                    except Exception as e:
                        logger.error(f"Erro ao remover motorista: {e}")
                        self.send_message(chat_id, f"[ERRO] Erro ao remover: {e}")
                else:
                    self.send_message(chat_id, "[ERRO] Uso: /remove LH_1234567890123")

            elif mensagem.startswith('/add'):
                dados_para_adicionar = mensagem.replace('/add', '').strip()
                if dados_para_adicionar:
                    try:
                        resultado = self.bot_bolsao.adicionar_motoristas(dados_para_adicionar)
                        
                        if resultado['status'] == 'novo':
                            self.send_message(chat_id, f"[OK] {resultado['mensagem']}")
                            # Registra que este usuário adicionou este motorista
                            lh = dados_para_adicionar.split()[0]  # Extrai o LH da entrada
                            self.gerenciador_usuarios.adicionar_motorista(chat_id, lh)
                            logger.info(f"Motorista adicionado por {chat_id}: {lh}")
                        
                        elif resultado['status'] == 'duplicado':
                            self.send_message(
                                chat_id, 
                                f"[AVISO] {resultado['mensagem']}\n"
                                f"Dados existentes: Nome={resultado['dados']['Nome']}, "
                                f"Placa={resultado['dados']['Placas']}"
                            )
                            logger.warning(f"Tentativa de adicionar motorista duplicado: {dados_para_adicionar}")
                        
                        elif resultado['status'] == 'erro':
                            self.send_message(chat_id, f"[ERRO] {resultado['mensagem']}")
                            logger.error(f"Erro ao adicionar motorista: {resultado['mensagem']}")
                    
                    except Exception as e:
                        logger.error(f"Erro inesperado ao adicionar motorista: {e}", exc_info=True)
                        self.send_message(chat_id, f"[ERRO] Erro ao adicionar: {str(e)[:100]}")
                else:
                    self.send_message(chat_id, "[ERRO] Uso: /add LH_1234567890123 NOME PLACA")
            
            elif mensagem.startswith('/concluidos'):
                lh = mensagem.replace('/concluidos', '').strip()
                if lh:
                    # Valida se o usuário pode marcar este motorista
                    if not self.gerenciador_usuarios.pode_editar_motorista(chat_id, lh):
                        self.send_message(chat_id, "[ERRO] Você não tem permissão para marcar este motorista!\nVocê só pode editar motoristas que criou.")
                        logger.warning(f"Tentativa de marcar motorista sem permissão - Usuário: {chat_id}, Motorista: {lh}")
                        return
                    
                    try:
                        resultado = self.bot_bolsao.marcar_concluido(lh)
                        if resultado['status'] == 'sucesso':
                            self.send_message(chat_id, f"[OK] {resultado['mensagem']}")
                            logger.info(f"Motorista marcado como concluído por {chat_id}: {lh}")
                        else:
                            self.send_message(chat_id, f"[ERRO] {resultado['mensagem']}")
                    except Exception as e:
                        logger.error(f"Erro ao marcar como concluído: {e}")
                        self.send_message(chat_id, f"[ERRO] Erro: {e}")
                else:
                    self.send_message(chat_id, "[ERRO] Uso: /concluidos LH_1234567890123")
            
            elif mensagem.startswith('/cancelados'):
                lh = mensagem.replace('/cancelados', '').strip()
                if lh:
                    # Valida se o usuário pode marcar este motorista
                    if not self.gerenciador_usuarios.pode_editar_motorista(chat_id, lh):
                        self.send_message(chat_id, "[ERRO] Você não tem permissão para marcar este motorista!\nVocê só pode editar motoristas que criou.")
                        logger.warning(f"Tentativa de marcar motorista sem permissão - Usuário: {chat_id}, Motorista: {lh}")
                        return
                    
                    try:
                        resultado = self.bot_bolsao.marcar_cancelado(lh)
                        if resultado['status'] == 'sucesso':
                            self.send_message(chat_id, f"[OK] {resultado['mensagem']}")
                            logger.info(f"Motorista marcado como cancelado por {chat_id}: {lh}")
                        else:
                            self.send_message(chat_id, f"[ERRO] {resultado['mensagem']}")
                    except Exception as e:
                        logger.error(f"Erro ao marcar como cancelado: {e}")
                        self.send_message(chat_id, f"[ERRO] Erro: {e}")
                else:
                    self.send_message(chat_id, "[ERRO] Uso: /cancelados LH_1234567890123")
            
            elif mensagem == '/planilha' or mensagem.startswith('/planilha'):
                # Extrai senha se foi fornecida
                senha_fornecida = mensagem.replace('/planilha', '').strip()
                
                # Verifica se a senha foi fornecida
                if not senha_fornecida:
                    self.send_message(chat_id, "[AVISO] Esta planilha requer senha.\nUso: /planilha SENHA")
                    return
                
                # Valida a senha
                if senha_fornecida != self.senha_planilha:
                    logger.warning(f"Tentativa de acessar planilha com senha incorreta")
                    self.send_message(chat_id, "[ERRO] Senha incorreta! Acesso negado.")
                    return
                
                try:
                    # Gera relatório
                    relatorio = self.bot_bolsao.obter_relatorio_fechamento()
                    if not relatorio:
                        self.send_message(chat_id, "[AVISO] Nenhum motorista registrado para gerar planilha.")
                        return
                    
                    logger.info(f"Acesso à planilha permitido para {chat_id}")
                    
                    # Cria/atualiza planilha
                    threading.Thread(
                        target=self._gerar_e_enviar_planilha,
                        args=(chat_id, relatorio),
                        daemon=True
                    ).start()
                except Exception as e:
                    logger.error(f"Erro ao processar planilha: {e}")
                    self.send_message(chat_id, f"[ERRO] Erro ao gerar planilha: {e}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
    
    def _gerar_e_enviar_planilha(self, chat_id, relatorio):
        """Gera e envia a planilha de fechamento."""
        try:
            self.send_message(chat_id, "[INFO] Gerando planilha de fechamento...")
            
            # Debug
            logger.info(f"Relatório recebido: {len(relatorio)} motoristas")
            if relatorio:
                logger.debug(f"Primeiro registro: {relatorio[0]}")
            
            # Cria/atualiza planilha
            caminho = self.planilha.criar_ou_atualizar_planilha(relatorio)
            logger.info(f"Planilha criada: {caminho}")
            
            # Envia arquivo
            if self.enviar_arquivo(chat_id, caminho):
                self.send_message(
                    chat_id,
                    "[OK] Planilha de fechamento enviada!\n"
                    "Cores:\n"
                    "- Amarelo = Motorista Ativo\n"
                    "- Verde = Motorista Concluido\n"
                    "- Vermelho = Motorista Cancelado"
                )
            else:
                self.send_message(chat_id, "[ERRO] Falha ao enviar planilha.")
                logger.error(f"Falha ao enviar planilha para {chat_id}")
        
        except Exception as e:
            logger.error(f"Erro ao gerar/enviar planilha: {e}", exc_info=True)
            self.send_message(chat_id, f"[ERRO] Erro ao processar planilha: {str(e)[:100]}")
    
    def _enviar_ajuda(self, chat_id):
        """Envia mensagem de ajuda com lista de comandos."""
        mensagem_ajuda = """
[AJUDA] - Comandos Disponiveis:

/login <SENHA>
  Realiza login no sistema (necessário para usar os comandos).
  Exemplo: /login MinhaS3nh4

/add <LH> <NOME> <PLACA>
  Adiciona um novo motorista ao sistema.
  Exemplo: /add LH1234567890123 Joao Silva ABC1234

/placa <PLACA>
  Busca motorista pela placa (7 caracteres).
  Exemplo: /placa ABC1234

/lh <LH>
  Busca motorista pela LH (13 caracteres).
  Exemplo: /lh LH1234567890123

/remove <LH>
  Remove motorista do sistema (marca como cancelado).
  Exemplo: /remove LH1234567890123

/concluidos <LH>
  Marca motorista como concluido (verde na planilha).
  Exemplo: /concluidos LH1234567890123

/cancelados <LH>
  Marca motorista como cancelado (vermelho na planilha).
  Exemplo: /cancelados LH1234567890123

/planilha <SENHA>
  Gera e envia planilha de fechamento com cores.
  Requer senha de segurança.
  - Amarelo = Ativo
  - Verde = Concluido
  - Vermelho = Cancelado

/help
  Mostra esta mensagem de ajuda.

Duvidas? Entre em contato com o suporte!
"""
        self.send_message(chat_id, mensagem_ajuda)
        logger.info(f"Ajuda enviada para {chat_id}")
    
    def pesquisa_placa_async(self, chat_id, placa):
        """Busca por placa em thread separada e envia resposta automaticamente."""
        try:
            logger.info(f"Iniciando busca por placa: {placa}")
            placa_pesquisada = self.bot_bolsao.pesquisar_motoristas(placa)
            if placa_pesquisada:
                resposta = f"[OK] Motorista encontrado: {placa_pesquisada}"
                logger.info(f"Placa encontrada: {placa}")
                self.send_message(chat_id, resposta)
            else:
                resposta = f"[FALHA] Nenhum motorista encontrado para placa {placa}"
                logger.info(f"Placa não encontrada: {placa}")
                self.send_message(chat_id, resposta)
        except Exception as e:
            logger.error(f"Erro na busca de placa {placa}: {e}", exc_info=True)
            self.send_message(chat_id, f"[ERRO] Erro na busca: {str(e)[:100]}")

    def pesquisa_lh_async(self, chat_id, lh):
        """Busca por LH em thread separada e envia resposta automaticamente."""
        try:
            logger.info(f"Iniciando busca por LH: {lh}")
            lh_pesquisada = self.bot_bolsao.pesquisar_motoristas(lh)
            if lh_pesquisada:
                resposta = f"[OK] Motorista encontrado: {lh_pesquisada}"
                logger.info(f"LH encontrado: {lh}")
                self.send_message(chat_id, resposta)
            else:
                resposta = f"[FALHA] Nenhum motorista encontrado para LH {lh}"
                logger.info(f"LH não encontrado: {lh}")
                self.send_message(chat_id, resposta)
        except Exception as e:
            logger.error(f"Erro na busca de LH {lh}: {e}", exc_info=True)
            self.send_message(chat_id, f"❌ Erro na busca: {str(e)[:100]}")

    def send_message(self, chat_id, text):
        """Envia mensagem com retry automático."""
        if not self.link_base:
            logger.error("link_base não está configurado")
            return False
        
        url = self.link_base + "sendMessage"
        for tentativa in range(1, 3):  # 2 tentativas
            try:
                response = requests.post(
                    url, 
                    data={"chat_id": chat_id, "text": text},
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    logger.info(f"Mensagem enviada para {chat_id}")
                    return True
                else:
                    logger.warning(f"Status {response.status_code} ao enviar para {chat_id}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Erro ao enviar (tentativa {tentativa}): {e}")
                if tentativa < 2:
                    time.sleep(1)
                continue
        
        logger.error(f"Falha ao enviar mensagem para {chat_id}")
        return False
    
    def enviar_arquivo(self, chat_id, caminho_arquivo):
        """Envia arquivo para o Telegram."""
        if not self.link_base or not Path(caminho_arquivo).exists():
            logger.error(f"Arquivo não encontrado: {caminho_arquivo}")
            return False
        
        url = self.link_base + "sendDocument"
        try:
            with open(caminho_arquivo, 'rb') as f:
                files = {'document': f}
                response = requests.post(
                    url,
                    data={"chat_id": chat_id},
                    files=files,
                    timeout=60
                )
            if response.status_code == 200:
                logger.info(f"Arquivo enviado para {chat_id}: {caminho_arquivo}")
                return True
            else:
                logger.error(f"Erro ao enviar arquivo: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Erro ao enviar arquivo: {e}")
            return False
    
    def receive_message(self):
        get = self.link_base + "getUpdates"
        response = requests.get(get)
        return response.json()

    def configure_token(self):
        """Configura o token do bot com validação."""
        try:
            load_dotenv(Path(__file__).parent / ".env")
            self.token = os.getenv("token_telegram")
            if not self.token:
                logger.error("Token não encontrado no arquivo .env")
                raise ValueError("Variável 'token_telegram' não configurada no .env")
            self.link_base = f"https://api.telegram.org/bot{self.token}/"
            
            # Carrega senha da planilha
            self.senha_planilha = os.getenv("senha_planilha")
            if not self.senha_planilha:
                logger.error("Senha da planilha não encontrada no arquivo .env")
                raise ValueError("Variável 'senha_planilha' não configurada no .env")
            
            # Carrega senha de autenticação
            self.senha_autenticacao = os.getenv("senha_autenticacao")
            if not self.senha_autenticacao:
                logger.error("Senha de autenticação não encontrada no arquivo .env")
                raise ValueError("Variável 'senha_autenticacao' não configurada no .env")
            
            logger.info("Token, senha de planilha e autenticação configurados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao configurar token/senha: {e}")
            raise
    
    def extrair_dados(json_data):
        """
        Extrai os dados necessários do JSON retornado pela API do Telegram.

        Args:
            json_data (dict): O JSON retornado pela API do Telegram.

        Returns:
            tuple: Uma tupla contendo o chat_id e o texto da mensagem.
        """
        try:
            resultados = json_data.get('result', [])
            if not resultados:
                return None, None
            
            ultima_atualizacao = resultados[-1]
            mensagem = ultima_atualizacao.get('message', {})
            chat_id = mensagem.get('chat', {}).get('id', None)
            texto = mensagem.get('text', None)
            
            return chat_id, texto
        except Exception as e:
            print(f"Erro ao extrair dados: {e}")
            return None, None

    def clear_history(self, keep_last_n: int = 0):
        """Descarta updates antigos no servidor do Telegram com retry."""
        if not self.token:
            raise RuntimeError("token não configurado. Chame configure_token() antes de clear_history().")

        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro ao limpar histórico: {e}")
            return
        
        if not data.get('ok'):
            logger.warning(f"API retornou erro ao limpar: {data.get('description')}")
            return
        
        results = data.get('result', [])
        if not results:
            logger.info("Nenhum update pendente para limpar")
            return

        # identifica o maior update_id disponível
        max_id = results[-1].get('update_id')
        if max_id is None:
            return

        if keep_last_n <= 0:
            new_offset = max_id + 1
        else:
            new_offset = max_id - (keep_last_n - 1)
            if new_offset < 0:
                new_offset = 0

        # chama getUpdates com offset para que o Telegram descarte as anteriores
        try:
            requests.get(url, params={"offset": new_offset}, timeout=self.timeout)
            logger.info(f"Histórico limpo: offset={new_offset} (mantendo {keep_last_n} mensagens)")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro ao definir offset: {e}")
        
if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("[BOT] Iniciando Bot Telegram para Busca de Motoristas")
        logger.info("=" * 60)
        
        bot_b = RoboBolsao()
        bot = BotTelegram(bot_bolsao=bot_b, token=None, texto=None, chat_id=None)
        bot.configure_token()
        bot.rodarbot()
    except KeyboardInterrupt:
        logger.info("Bot interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro crítico ao iniciar bot: {e}", exc_info=True)
        raise