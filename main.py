from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/calendar.events"
]


def autenticar():
    creds = None

    # Se já autenticou anteriormente
    try:
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )
    except FileNotFoundError:
        pass

    # Se ainda não estiver autenticado
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # Salva a autorização para as próximas execuções
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def criar_evento():

    creds = autenticar()

    service = build(
        "calendar",
        "v3",
        credentials=creds
    )

    inicio = datetime(2026, 9, 5, 15, 0)
    fim = inicio + timedelta(hours=1)

    evento = {
        "summary": "TESTE - Reserva Acadêmica",

        "description": (
            "Este evento foi criado pelo "
            "sistema de reservas."
        ),

        "start": {
            "dateTime": inicio.isoformat(),
            "timeZone": "America/Sao_Paulo"
        },

        "end": {
            "dateTime": fim.isoformat(),
            "timeZone": "America/Sao_Paulo"
        }
    }

    resultado = service.events().insert(
        calendarId="primary",
        body=evento
    ).execute()

    print("Evento criado com sucesso!")
    print("Link:")
    print(resultado.get("htmlLink"))


criar_evento()