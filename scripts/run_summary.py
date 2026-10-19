"""Report each consultation in Actions without adding notices to the profile."""
from datetime import datetime, timezone
from pathlib import Path
import json, os

ROOT = Path(__file__).resolve().parents[1]


def main():
    changed = os.getenv('PROFILE_CHANGED')
    status = os.getenv('PROFILE_RUN_STATUS', 'unknown')
    labels = {'success': 'concluída', 'failure': 'falhou', 'cancelled': 'cancelada',
              'skipped': 'dispensada'}
    lines = ['## Atualização do perfil', '',
             '- Consulta: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
             '- Disparo: ' + os.getenv('PROFILE_EVENT', 'local'),
             '- Resultado: ' + labels.get(status, status),
             '- Coleta do calendário: ' + labels.get(os.getenv('PROFILE_CALENDAR_STATUS'), 'não executada'),
             '- Publicação das imagens: ' + labels.get(os.getenv('PROFILE_DEPLOY_STATUS'), 'não executada')]
    calendar = ROOT / 'data/contributions.json'
    if calendar.exists():
        data = json.loads(calendar.read_text(encoding='utf-8'))
        lines.extend(['- Data dos dados disponíveis: ' + data['as_of'],
                      '- Contribuições no período: ' + str(data['stats']['total'])])
    if changed == 'false' and status == 'success':
        lines.extend(['', 'Dados consultados com sucesso, sem alterações no painel. '
                      'Nenhum novo commit foi necessário.'])
    elif changed == 'true' and status == 'success':
        lines.extend(['', 'Dados e arte atualizados. As imagens foram publicadas antes dos links do README.'])
    elif status != 'success':
        lines.extend(['', 'Consulte a etapa que falhou nos logs. O último painel válido permanece disponível.'])
    lines.extend(['', 'Agendamento: a cada 5 minutos; o disparo pode atrasar no GitHub Actions.'])
    summary = '\n'.join(lines) + '\n'
    destination = os.getenv('GITHUB_STEP_SUMMARY')
    if destination:
        with open(destination, 'a', encoding='utf-8') as file:
            file.write(summary)
    print(summary)


if __name__ == '__main__':
    main()
