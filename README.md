# 🏠 Casa Inteligente: automação residencial com ESP32
 
Projeto acadêmico (M2) de automação residencial feito com ESP32 e MicroPython, simulado no Wokwi dentro do Visual Studio Code.
 
## 📖 Sobre o projeto
 
A ideia é simular uma casa que "sente" o ambiente e reage a ele. Um ESP32 lê quatro sensores, aciona quatro dispositivos e conversa com o mundo de fora por MQTT. A partir daí, o morador pode acompanhar e controlar tudo de três lugares diferentes: uma página web hospedada no próprio ESP32, um dashboard no Node-RED e um display OLED ligado à placa.
 
Quando algo foge do normal (temperatura alta, movimento ou objeto perto do portão), o sistema gera um alerta, registra em uma planilha do Google Sheets e avisa o proprietário por e-mail.
 
### O que o sistema controla
 
| Dispositivo | O que representa na casa | Como é controlado |
|---|---|---|
| LED vermelho | Luz da sala | Ligar / desligar |
| LED azul | Luz do quarto | Ligar / desligar |
| Servo motor | Portão da garagem | Abrir (90°) / fechar (0°) |
| Buzzer | Ventilador | Automático / ligar / desligar |
 
### O que o sistema monitora
 
| Sensor | O que mede |
|---|---|
| DHT22 | Temperatura e umidade do ar |
| HC-SR04 | Distância de um objeto até o portão |
| PIR | Presença de movimento |
| LDR | Luminosidade do ambiente |
 
## 🧰 Tecnologias utilizadas
 
- ESP32 programado em MicroPython
- Wokwi (simulador) e Visual Studio Code
- MQTT, usando o broker público HiveMQ
- Node-RED (Dashboard 2.0), executado em Docker
- HTML, CSS e JavaScript para a página do ESP32
- Google Sheets e Google Apps Script
- `mpremote` para enviar os arquivos à placa simulada
## 🔌 Componentes e pinagem
 
| Tipo | Componente | GPIO | Função |
|---|---|---|---|
| Sensor | DHT22 | 15 | Temperatura e umidade |
| Sensor | HC-SR04 | TRIG 5 / ECHO 18 | Distância |
| Sensor | PIR | 19 | Movimento |
| Sensor | LDR (módulo) | 34 | Luminosidade |
| Atuador | LED vermelho | 25 | Luz da sala |
| Atuador | LED azul | 26 | Luz do quarto |
| Atuador | Servo motor | 27 | Portão |
| Atuador | Buzzer | 23 | Ventilador |
| Display | OLED SSD1306 | SDA 21 / SCL 22 | Situação da casa e alertas |
 
O diagrama completo está em `diagram.json`.
 
## ⚙️ Funcionalidades
 
- Leitura de temperatura, umidade, distância, movimento e luminosidade a cada 5 segundos.
- Controle individual de cada atuador, pela página web, pelo Node-RED ou por qualquer cliente MQTT.
- Ventilador com modo automático: liga a partir de 30 °C e desliga em 28 °C ou menos.
- Alertas de temperatura alta, movimento detectado e objeto a 20 cm ou menos do portão. Cada alerta é enviado uma vez, quando o evento começa.
- Display OLED com os valores dos sensores, o estado do ventilador e o último alerta.
- Dashboard no Node-RED com os dados em tempo real, os botões de controle e o histórico dos últimos alertas.
- Registro dos sensores no Google Sheets a cada 2 horas e de cada alerta, com envio de e-mail ao proprietário.
## 📡 Como as partes se comunicam
 
```
Sensores ─► ESP32 ──MQTT──► HiveMQ ──► Node-RED ──► Dashboard
Atuadores ◄─┘   ▲                          │
                │                          ├──► Google Sheets (Apps Script)
        Página web (porta 80)              └──► E-mail ao proprietário
```
 
O ESP32 publica as leituras e os alertas no broker e assina os tópicos de comando. O Node-RED recebe os dados, mostra no dashboard e publica comandos de volta quando um botão é clicado. Como a página web e o MQTT usam as mesmas funções de controle, um comando vindo de qualquer lado atualiza o mesmo atuador.
 
### Tópicos MQTT
 
O prefixo é definido em `secrets.py` (`MQTT_PREFIXO`) e precisa ser o mesmo no Node-RED.
 
| Tópico | Sentido | Conteúdo |
|---|---|---|
| `<prefixo>/telemetria` | ESP32 → Node-RED | JSON com sensores e estado dos atuadores |
| `<prefixo>/alertas` | ESP32 → Node-RED | JSON com tipo, mensagem e valor |
| `<prefixo>/status` | ESP32 → Node-RED | `online` |
| `<prefixo>/atuadores/luz_sala` | Node-RED → ESP32 | `ON` / `OFF` |
| `<prefixo>/atuadores/luz_quarto` | Node-RED → ESP32 | `ON` / `OFF` |
| `<prefixo>/atuadores/portao` | Node-RED → ESP32 | `ABRIR` / `FECHAR` |
| `<prefixo>/atuadores/ventilador` | Node-RED → ESP32 | `AUTO` / `ON` / `OFF` |
 
## 📁 Estrutura do projeto
 
```
Projeto automação/
├── main.py                       # código principal do ESP32
├── index.html                    # página web servida pelo ESP32
├── ssd1306.py                    # driver do display OLED
├── secrets_exemplo.py            # modelo das credenciais
├── fluxo_node_red.json           # fluxo exportado do Node-RED
├── rodar.ps1                     # envia os arquivos ao ESP32 (Windows)
├── firmware.bin                  # firmware MicroPython
├── diagram.json                  # circuito do Wokwi
├── wokwi.toml                    # configuração do simulador
├── README.md
└── .gitignore
```
 
O arquivo `secrets.py` guarda as configurações locais e **não deve ser enviado ao repositório**.
 
## 🚀 Como executar
 
**Pré-requisitos:** VS Code com a extensão Wokwi, Python, Docker Desktop e a ferramenta `mpremote` (`pip install mpremote`).
 
### 1. Configurar as credenciais
 
Copie o modelo e ajuste os valores:
 
```powershell
copy secrets_exemplo.py secrets.py
```
 
```python
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_PREFIXO = "casa-inteligente-m2-umc"   # use um prefixo só seu
MQTT_CLIENT_ID = "esp32-casa-m2-umc"       # precisa ser único no broker
```
 
### 2. Subir o Node-RED
 
```powershell
docker run -it -p 1880:1880 -v node_red_data:/data --name meu-nodered nodered/node-red
```
 
Se o container já existe, basta iniciá-lo (`docker start meu-nodered`). Depois:
 
1. Abra `http://localhost:1880`.
2. Em **Manage palette → Install**, instale `node-red-node-email`.
3. Em **Import**, selecione `fluxo_node_red.json` e clique em **Deploy**.
4. Nos dois nós de planilha, cole a URL do Apps Script (veja a seção do Google Sheets) e, no nó de e-mail, preencha o destinatário e a senha de app do remetente.
O dashboard fica em `http://localhost:1880/dashboard/casa`.
 
### 3. Enviar os arquivos e iniciar a simulação
 
A memória do ESP32 simulado é apagada toda vez que a simulação reinicia, então os arquivos precisam ser enviados de novo. A ordem importa:
 
1. Abra **um** terminal na pasta do projeto e rode `.\rodar.ps1`. Ele fica em "Aguardando o simulador...".
2. Inicie o simulador (F1 → **Wokwi: Start Simulator**).
3. O script envia os arquivos, reinicia a placa e o `main.py` começa a rodar.
Para reenviar depois de alterar o código, pare o simulador, espere alguns segundos e inicie de novo, com o script ainda aberto.
 
> Alternativa em bash: com o simulador já iniciado, rode `bash upload.sh`.
 
### 4. Acessar a página web do ESP32
 
```
http://localhost:8180
```
 
O `wokwi.toml` encaminha a porta 8180 do computador para a porta 80 do ESP32.
 
### 5. Configurar o Google Sheets
 
1. Crie uma planilha com duas abas: **Sensores** e **Alertas**.
2. Em **Extensões → Apps Script**, cole:
```javascript
function doPost(e) {
  const d = JSON.parse(e.postData.contents);
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const aba = ss.getSheetByName(d.aba) || ss.insertSheet(d.aba);
  aba.appendRow(d.linha);
  return ContentService.createTextOutput('ok');
}
```
 
3. Em **Implantar → Nova implantação → App da Web**, escolha executar como **Eu** e dar acesso a **Qualquer pessoa**. Copie a URL gerada.
## 🧪 Como testar
 
Com tudo rodando, estas ações mostram cada parte do sistema funcionando:
 
| O que fazer | O que deve acontecer |
|---|---|
| No Wokwi, subir a temperatura do DHT22 para 30 °C ou mais | O buzzer (ventilador) liga no modo automático; o alerta aparece no dashboard, no OLED, na planilha e no e-mail |
| Clicar no sensor PIR | Alerta de movimento detectado |
| Aproximar o objeto do HC-SR04 (20 cm ou menos) | Alerta de objeto próximo ao portão |
| Alterar a luminosidade do LDR | O valor muda no card de luminosidade |
| No dashboard, **Ligar** a luz da sala | O LED vermelho acende; o card muda para "Ligada" |
| No dashboard, **Abrir** o portão | O servo gira para 90° |
| No dashboard, escolher **Automático**, **Ligar** ou **Desligar** no ventilador | O buzzer responde ao modo escolhido |
| Repetir os comandos pela página `localhost:8180` | O mesmo efeito no simulador, refletido também no Node-RED |
| No Node-RED, clicar no botão do nó "A cada 2 horas" | Uma nova linha aparece na aba **Sensores** da planilha |
 
Se o card do Node-RED demorar a atualizar depois de um clique, é normal: o estado volta na próxima telemetria, em até 5 segundos.
 
## ⚠️ Observações
 
- Após reiniciar a simulação do Wokwi, os arquivos precisam ser enviados novamente ao ESP32.
- O HiveMQ público é compartilhado entre muitos usuários. Use um prefixo de tópico único para não misturar mensagens.
---
  
Projeto acadêmico desenvolvido para aplicar conceitos de Internet das Coisas (IoT) com ESP32 e MicroPython.

**Autor:** Vitória Rodrigues de Souza · UMC, Engenharia de Software
