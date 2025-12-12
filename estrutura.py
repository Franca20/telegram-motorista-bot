"""
Criar uma classe estruturada para organizar meu codigo
"""
import time
from datetime import datetime

data = time.localtime()
data_atual =  f'{data.tm_mday}/{data.tm_mon}/{data.tm_year} {data.tm_hour}:{data.tm_min}'

class RoboBolsao:
    def __init__(self):
        self.dados_motoristas = {}
        self.historico_status = {}  # Rastreia status: 'ativo', 'concluido', 'cancelado'

    # funcao pacialmente terminada
    def adicionar_motoristas(self, dado):
        """Adiciona motorista com validação de duplicata.
        
        Retorna:
            dict: {'status': 'novo'|'duplicado'|'erro', 'mensagem': str, 'dados': dict|None}
        """
        try:
            dados_tratados = {}
            dados_separados = dado.split()
            dados_tratados['LH'] = dados_separados[0]
            dados_separados.pop(0)
            dados_tratados['Placas'] = dados_separados[-1]
            dados_separados.pop(-1)
            nome = ' '.join(dados_separados)
            dados_tratados['Nome'] = nome
            
            # Use LH as the key to store the motorista dictionary
            lh = dados_tratados['LH']
            
            # Verifica se LH já existe
            if lh in self.dados_motoristas:
                return {
                    'status': 'duplicado',
                    'mensagem': f'Motorista com LH {lh} já existe no sistema.',
                    'dados': self.dados_motoristas[lh]
                }
            
            # Adiciona o novo motorista
            self.dados_motoristas[lh] = dados_tratados
            return {
                'status': 'novo',
                'mensagem': f'Motorista {nome} ({lh}) adicionado com sucesso.',
                'dados': dados_tratados
            }
        
        except IndexError as e:
            return {
                'status': 'erro',
                'mensagem': 'Formato inválido. Use: /add LH_NUMERO NOME PLACA',
                'dados': None
            }
        except Exception as e:
            return {
                'status': 'erro',
                'mensagem': f'Erro ao tratar dados: {e}',
                'dados': None
            }
        
    # funcao pacialmente terminada
    def pesquisar_motoristas(self, valor_pesquisa):
        resultado = []
        p_user = valor_pesquisa.lower()
        q_caracter = len(p_user)

        if q_caracter == 7:
            # Buscar por placa (7 caracteres)
            for chave, motorista_dict in self.dados_motoristas.items():
                if isinstance(motorista_dict, dict):
                    placa = motorista_dict.get('Placas', '').lower()

                    if len(placa) > 7:
                        placas_lista = [p.strip() for p in placa.split(',')]
                        if p_user in placas_lista:
                            print(f'Motorista encontrado: {motorista_dict}') 
                            resultado.append(motorista_dict)
                            return resultado
                        
                    if placa == p_user:
                        print(f'Motorista encontrado: {motorista_dict}') 
                        resultado.append(motorista_dict)
                        return resultado

        elif q_caracter == 13:
            # Buscar por LH (13 caracteres)
            for chave, motorista_dict in self.dados_motoristas.items():
                if isinstance(motorista_dict, dict):
                    lh = motorista_dict.get('LH', '').lower()
                    if lh == p_user:
                        print(f'Motorista encontrado: {motorista_dict}')
                        resultado.append(motorista_dict)
                        return resultado
        else:
            text = 'Valor de pesquisa invalido. Insira uma Placa (7 caracteres) ou LH (13 caracteres).'
            print(text)
            return text
    
    # funcao pacialmente terminada
    def remover_motorista(self, dado_remover):
        """Remove motorista e marca status como cancelado no histórico."""
        try:
            if dado_remover in self.dados_motoristas:
                motorista = self.dados_motoristas.pop(dado_remover)
                # Registra no histórico como cancelado
                self.historico_status[dado_remover] = {
                    'motorista': motorista,
                    'status': 'cancelado',
                    'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
                    'motivo': 'removido'
                }
                return {'status': 'sucesso', 'mensagem': f'Motorista {motorista["Nome"]} removido com sucesso.'}
            else:
                return {'status': 'erro', 'mensagem': 'Motorista não encontrado.'}
        except Exception as e:
            return {'status': 'erro', 'mensagem': f'Erro ao remover: {e}'}
    
    def marcar_concluido(self, lh):
        """Marca motorista como concluído."""
        if lh not in self.dados_motoristas:
            return {'status': 'erro', 'mensagem': 'Motorista não encontrado.'}
        
        motorista = self.dados_motoristas[lh]
        self.historico_status[lh] = {
            'motorista': motorista,
            'status': 'concluido',
            'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'motivo': 'concluído'
        }
        return {
            'status': 'sucesso',
            'mensagem': f'Motorista {motorista["Nome"]} marcado como concluído.',
            'dados': motorista
        }
    
    def marcar_cancelado(self, lh):
        """Marca motorista como cancelado."""
        if lh not in self.dados_motoristas:
            return {'status': 'erro', 'mensagem': 'Motorista não encontrado.'}
        
        motorista = self.dados_motoristas[lh]
        self.historico_status[lh] = {
            'motorista': motorista,
            'status': 'cancelado',
            'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'motivo': 'cancelado'
        }
        return {
            'status': 'sucesso',
            'mensagem': f'Motorista {motorista["Nome"]} marcado como cancelado.',
            'dados': motorista
        }
    
    def obter_relatorio_fechamento(self):
        """Retorna lista de todos os motoristas com status (ativos + histórico).
        
        Não duplica motoristas que estão no histórico.
        """
        relatorio = []
        
        # Motoristas ativos (que NÃO estão no histórico)
        for lh, motorista in self.dados_motoristas.items():
            # Só adiciona se NÃO está no histórico (não foi marcado como concluído/cancelado)
            if lh not in self.historico_status:
                relatorio.append({
                    'LH': motorista.get('LH', ''),
                    'Nome': motorista.get('Nome', ''),
                    'Placa': motorista.get('Placas', ''),
                    'Status': 'Ativo',
                    'Data': datetime.now().strftime('%d/%m/%Y %H:%M')
                })
        
        # Histórico (concluídos e cancelados)
        for lh, historico in self.historico_status.items():
            relatorio.append({
                'LH': lh,
                'Nome': historico['motorista'].get('Nome', ''),
                'Placa': historico['motorista'].get('Placas', ''),
                'Status': 'Concluido' if historico['status'] == 'concluido' else 'Cancelado',
                'Data': historico.get('data', '')
            })
        
        return relatorio

    def escrever_arquivo(self, nome_arquivo):
        try:
            with open(f'{nome_arquivo}_{data_atual}', 'w') as arquivo:
                for chave, valor in self.dados_motoristas.items():
                    linha = f'LH: {valor["LH"]}, Nome: {valor["Nome"]}, Placas: {valor["Placas"]}\n'
                    arquivo.write(linha)
            print('Dados escritos no arquivo com sucesso!')
        except Exception as e:
            print(f'Erro ao escrever no arquivo: {e}')