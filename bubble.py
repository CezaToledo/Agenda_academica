import os
import requests
import hashlib
import base64
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ============================================================
# 0.CONFIGURAÇÂO DO GOOGLE CALENDAR [DEFINA AS VARIÁVEIS PARA CONEXÃO COM A API ABAIXO]
# ============================================================

id_da_agenda_la = "c_b3acdb7273f250637317320ab1e39d080d1cf208a74df06174629cfd7980e56e@group.calendar.google.com" # insira aqui o ID público da agenda que será preenchida

esoupos = [ "https://www.googleapis.com/auth/calendar.events" ] # define que a api do google calendar será usada

arquivo_super_secreto = "credentials.json" # Insira o arquivo com as credenciais
arquivo_mais_secreto_ainda = "token.json" # Insira aqui o arquivo com os tokens & secrets

# ============================================================
# 0.1.CONFIGURAÇÃO DA API DO BUBBLE [DEFINE AS VARIÁVEIS USADAS PARA ACESSO DA API DO BUBBLE.IO]
# ============================================================

BUBBLE_BASE_URL = "https://reservaslasalle.com.br" # URL base do site no bubble    

BUBBLE_RESERVA_URL = f"{BUBBLE_BASE_URL}/api/1.1/obj/reserva" # URL de acesso as reservas do bubble  (USE f"" em prints para inserir dados dinâmicos)
BUBBLE_SALA_URL = f"{BUBBLE_BASE_URL}/api/1.1/obj/sala" # URL de acesso as salas do bubble

# ============================================================
# 1.CONECTAR COM O GUGU AGENDAS
# ============================================================

def jarvis_conectar_gugu_agendas(): # simplesmente uma linha usada para definir uma função, só coloque def e um nome qualquer, deixe os parenteses vazios se não depender de nenhum outro objeto para rodar

    creds = None  # cria um dado vazio e nulo, só para ser usado posteriormente

    if os.path.exists(arquivo_mais_secreto_ainda): # testa SE existe um caminho pelo os para o arquivo de tokens
        creds = Credentials.from_authorized_user_file( # define aquela função vazia de creds como as credenciais do arquivo especificado dentro desta função
            arquivo_mais_secreto_ainda, # Especifica o arquivo
            esoupos # especifica os escopos para a autorização
        )

    if not creds or not creds.valid: # se não tiver credenciais ou credenciais válidas:

        if creds and creds.expired and creds.refresh_token: # se houverem credenciais e elas estiverem expiradas, tenta atualiza-las
            creds.refresh(Request()) # pede para atualizar as credenciais

        else: # senão, só tenta dnv a autorização
            flow = InstalledAppFlow.from_client_secrets_file(
                arquivo_super_secreto,
                esoupos
            )

            creds = flow.run_local_server(port=0) # roda localmente

        with open(arquivo_mais_secreto_ainda, "w") as token: # abre o arquivo para escrever nele
            token.write(creds.to_json()) # escreve as credenciais conseguidas para o arquivo

    service = build( # build cria um objeto para interação com a API
        "calendar",
        "v3",
        credentials=creds
    )

    return service # retorna 'service', que é a autorização do uso da api do calendar

# ============================================================
# 2.BUSCAR SALAS
# ============================================================

def buscar_salas(): # define a função de busca de salas
    response = requests.get(
        BUBBLE_SALA_URL # define que a variável de respostas é um pedido á API DO BUBBLE usando esta url
    )

    response.raise_for_status() # interrompe em caso de erro. QUALIDADE DE VIDA

    return response.json()["response"]["results"] # específica mais fundo quais dados quer


# ============================================================
# 3.CRIAR MAPA DE SALAS
# ============================================================

def criar_mapa_salas(): # cria o mapa das salas para usar o nome
    salas = buscar_salas() # define a lista de salas como o resultado da função 'buscar_salas'

    mapa = {} # cria um dicionário de salas vazio, o que tem como objetivo traduzir os ID's das salas para os nomes

    for sala in salas: # pra cada sala dentro da lista 'salas'

        id_sala = sala.get("_id") # pega o id
        nome_sala = sala.get("Nome") # pega o nome

        # Algumas salas podem estar sem nome
        if not nome_sala:
            print(
                f"⚠️ Sala {id_sala} está sem nome. " # avisa e ignora se uma sala não tem nome
                f"Ignorando."
            )
            continue # daí continua mesmo se n tiver um nome

        mapa[id_sala] = nome_sala # usa o mapa para a tradução

    print(  # manda a mensagem de quantas salas sem nome foram encontradas
        f"Salas com nome encontradas: "
        f"{len(mapa)}"
    )

    return mapa # entrega o mapa de salas

# ============================================================
# 4.BUSCAR RESERVAS
# ============================================================

def buscar_reservas(): # Função 'buscar_reservas' (não precisa de informação para rodar)
    todas_reservas = [] # lista vazia de reservas
    cursor = 0 # cursor para paginação

    while True: # loop de pesquisa
        params = {
            "cursor": cursor
        }

        response = requests.get( # armazena a resposta da requisição
            BUBBLE_RESERVA_URL,
            params=params
        )

        response.raise_for_status() # busca por erros

        dados = response.json()["response"] # transforma o json em python
        reservas = dados["results"]

        print( # mostra texto que explica o estado do cursor
            f"Cursor {cursor}: "
            f"{len(reservas)} reservas encontradas"
        )

        todas_reservas.extend(reservas) # adiciona as reservas á lista

        # Se veio menos que o tamanho do lote
        # chegamos ao final
        if len(reservas) < 100:
            break # para o loop

        cursor += len(reservas)

    print( # mostra o total de reservas recebidas
        f"\nTotal de reservas recebidas: "
        f"{len(todas_reservas)}"
    )

    return todas_reservas # faz a função entregar a lista(retornar)

# ============================================================
# 5.FILTRAR RESERVAS
# ============================================================

def reserva_deve_ser_exibida(reserva): # define a função, que precisa de uma reserva para continuar

    estado = reserva.get("estado") # pega o estado(inativo/ativo) da reserva
    inicio = reserva.get("Inicio") # pega o horário de início da reserva

    # Verificação de segurança
    if not inicio: # quando a reserva não tem um início, ela avisa e ignora
        print(
            f"⚠️ Reserva {reserva.get('_id')} "
            f"não possui data de início."
        )
        return False

    agora = datetime.now(timezone.utc) # pega o horário de agora(horário quando a reserva é executada)

    inicio_data = datetime.fromisoformat( # transforma a data do formato ISO
        inicio.replace("Z", "+00:00")
    )

    # Somente reservas ativas
    if estado != "Ativo": # ignora a reserva se o estado dela não for ativo
        return False

    if inicio_data <= agora: # ignora a reserva se ela for antiga
        return False

    return True # testa tudo e valida a reserva

# ============================================================
# 6.ADICIONAR UMA RESERVA COMO EVENTO NA AGENDA
# ============================================================

def criar_reserva_foda(service, reserva, mapa_salas):

    nome = reserva.get("Nome reserva")
    descricao = reserva.get("Descrição reserva")
    inicio = reserva.get("Inicio")
    fim = reserva.get("Fim")
    id_sala = reserva.get("Sala reservada")

    nome_sala = mapa_salas.get(id_sala, "Sala não identificada")

    event_id = gerar_event_id(reserva)

    evento = {
        "id": event_id,
        "summary": nome,
        "description": descricao,
        "location": nome_sala,
        "start": {
            "dateTime": inicio,
            "timeZone": "America/Sao_Paulo"
        },
        "end": {
            "dateTime": fim,
            "timeZone": "America/Sao_Paulo"
        }
    }

    try:

        evento_created_bro = service.events().insert(
            calendarId=id_da_agenda_la,
            body=evento
        ).execute()

        print(
            f"Evento Criado: {nome}"
        )

    except Exception as erro:

        if "409" in str(erro):

            print(f"Evento já existe: {nome}")

        else:

            print(f"Erro ao criar {nome}: {erro}")

# ============================================================
# 7.CRIAR ID DE RESERVA COMO EVENTO GOOGLE
# ============================================================

def gerar_event_id(reserva):

    reserva_id = reserva.get("_id")

    hash_bytes = hashlib.sha256(
        reserva_id.encode("utf-8")
    ).digest()

    event_id = base64.b32hexencode(
        hash_bytes
    ).decode("utf-8").lower().rstrip("=")

    return event_id[:100]

# ============================================================
# 8.MAIN
# ============================================================

def main():

    print("=" * 60)
    print("INICIANDO LEITURA DO BUBBLE")
    print("=" * 60)

    print("\nBuscando salas...")

    mapa_salas = criar_mapa_salas()

    print("\nBuscando reservas...")

    reservas = buscar_reservas()

    print("\nFiltrando reservas...")

    reservas_validas = []

    for reserva in reservas:

        if reserva_deve_ser_exibida(reserva):
            reservas_validas.append(reserva)

    print("\n" + "=" * 60)
    print("RESULTADO")
    print("=" * 60)

    print(
        f"Total de reservas recebidas: "
        f"{len(reservas)}"
    )

    print(
        f"Reservas ativas e futuras: "
        f"{len(reservas_validas)}"
    )

    print("=" * 60)

    print("\nTESTE DO FILTRO FINALIZADO.")

    print(
        f"Quantidade de reservas que seriam enviadas "
        f"para o Google: {len(reservas_validas)}"
    )

    # ========================================================
    # 8.1.CONECTAR AO GOOGLE CALENDAR
    # ========================================================

    print("\nConectando ao Google Calendar...")

    service = jarvis_conectar_gugu_agendas()

    print("✅ Google Calendar conectado!")

    # ========================================================
    # 8.2TESTAR UMA ÚNICA RESERVA
    # ========================================================

    if reservas_validas:

        print(f"\nCriando {len(reservas_validas)} eventos...")

        for reserva in reservas_validas:

            criar_reserva_foda(
                service,
                reserva,
                mapa_salas
            )

    else:

        print(
            "\n⚠️ Nenhuma reserva ativa e futura encontrada."
        )

    return reservas_validas, mapa_salas


# ============================================================
# 9.EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    reservas, mapa_salas = main()