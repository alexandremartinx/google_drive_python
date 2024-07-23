# google_drive_python

# Google Drive File Uploader
Este script Python autentica o usuário com o Google Drive, verifica se uma pasta existe, cria pastas e faz upload de arquivos e pastas locais para o Google Drive. Se os arquivos já existirem no Google Drive, eles são atualizados com a versão local.

# Funcionalidades
Autenticação com OAuth 2.0
Verificação de existência de pastas e arquivos no Google Drive
Criação de novas pastas no Google Drive
Upload de arquivos e pastas locais para o Google Drive
Atualização de arquivos existentes no Google Drive
Requisitos
Python 3.6 ou superior
Bibliotecas Python: google-auth, google-auth-oauthlib, google-auth-httplib2, google-api-python-client
Instalação

Clone o Repositório:

sh
git clone git@github.com:alexandremartinx/google_drive_python.git
cd google-drive-file-uploader

Crie e Ative um Ambiente Virtual:

sh
python -m venv venv
source venv/bin/activate No Windows, use `venv\Scripts\activate`

Instale as Dependências:

sh
pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
Configuração das Credenciais do Google Drive:

Acesse o Google Cloud Console.
Crie um novo projeto ou selecione um projeto existente.
Ative a API do Google Drive.
Crie credenciais do tipo "OAuth 2.0 Client IDs" e baixe o arquivo credentials.json.
Coloque o arquivo credentials.json no diretório do seu projeto.
Uso
Autenticação do Usuário:
O script autenticará o usuário com o Google Drive e salvará as credenciais em token.pickle. Se as credenciais expirarem, elas serão automaticamente atualizadas.

Upload de Pastas e Arquivos:
O script verifica se a pasta especificada já existe no Google Drive. Se existir, ele compara os arquivos dentro da pasta e substitui ou adiciona novos arquivos conforme necessário.

Execução do Script:

Edite o caminho da pasta local que deseja fazer upload no script (folder_path).

Execute o script:
sh
python main.py

# Estrutura do Código

authenticate_user():

Autentica o usuário com OAuth 2.0 e retorna o objeto de serviço do Google Drive.

find_folder(service, folder_name, parent_id='root'):
Verifica se uma pasta já existe no Google Drive e retorna seu ID.

find_file_in_folder(service, folder_id, file_name):
Verifica se um arquivo já existe dentro de uma pasta específica no Google Drive e retorna seu ID.

create_folder(service, folder_name, parent_id='root'):
Cria uma nova pasta no Google Drive e retorna seu ID.

upload_file(service, file_path, parent_id='root'):
Faz o upload de um arquivo para o Google Drive.

update_file(service, file_path, file_id):
Substitui um arquivo existente no Google Drive por um novo arquivo local.

upload_folder(service, folder_path, parent_id='root'):
Faz o upload de uma pasta inteira para o Google Drive, substituindo ou adicionando novos arquivos conforme necessário.

main():
Função principal que autentica o usuário, cria a pasta e faz o upload dos arquivos.