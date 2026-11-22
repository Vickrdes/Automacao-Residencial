# Bibliotecas
from machine import Pin, ADC, PWM, I2C, time_pulse_us
import dht
import time
import network
import ujson
import gc
from umqtt.simple import MQTTClient
import secrets


# Configuracoes Wi-Fi
WIFI_SSID = getattr(secrets, "WIFI_SSID", "Wokwi-GUEST")
WIFI_SENHA = getattr(secrets, "WIFI_PASS", "")


# Configuracoes MQTT
MQTT_BROKER = getattr(secrets, "MQTT_BROKER", "broker.hivemq.com")
MQTT_PORTA = getattr(secrets, "MQTT_PORT", 1883)

PREFIXO = getattr(secrets, "MQTT_PREFIXO")
MQTT_CLIENT_ID = getattr(secrets, "MQTT_CLIENT_ID")

TOPICO_TELEMETRIA = PREFIXO + "/telemetria"
TOPICO_ALERTAS = PREFIXO + "/alertas"
TOPICO_STATUS = PREFIXO + "/status"

TOPICO_LUZ_SALA = PREFIXO + "/atuadores/luz_sala"
TOPICO_LUZ_QUARTO = PREFIXO + "/atuadores/luz_quarto"
TOPICO_PORTAO = PREFIXO + "/atuadores/portao"
TOPICO_VENTILADOR = PREFIXO + "/atuadores/ventilador"

TOPICOS_CONTROLE = [
    TOPICO_LUZ_SALA,
    TOPICO_LUZ_QUARTO,
    TOPICO_PORTAO,
    TOPICO_VENTILADOR
]


# Configuracoes da automacao do ventilador (buzzer)
TEMP_LIGAR_VENTILADOR = 30
TEMP_DESLIGAR_VENTILADOR = 28

modo_ventilador = "AUTO"




# Configuracao dos sensores
# DHT22: Temperatura e umidade
dht_sensor = dht.DHT22(Pin(15))

# HC-SR04:  Distancia 
trig = Pin(5, Pin.OUT)
echo = Pin(18, Pin.IN)

# PIR: Movimento 
pir = Pin(19, Pin.IN)

# LDR: Luminosidade
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)


# Configuracao dos atuadores
# LED da sala: vermelho
led_sala = Pin(25, Pin.OUT)
led_sala.value(0)

# LED do quarto: azul 
led_quarto = Pin(26, Pin.OUT)
led_quarto.value(0)

# Servo: Portao 
servo = PWM(Pin(27), freq=50)

# Ventilador
buzzer = PWM(Pin(23), freq=1000, duty_u16=0)




# Display OLED
display = None

try:
    import ssd1306
    import sys

    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    print("I2C scan:", i2c.scan())   

    display = ssd1306.SSD1306_I2C(128, 64, i2c)

    # Mensagem imediata, antes do Wi-Fi e do MQTT
    display.fill(0)
    display.text("Iniciando...", 0, 0)
    display.show()

except Exception as erro:
    print("OLED indisponivel:", erro)
    sys.print_exception(erro)


# Estados dos atuadores
estado_luz_sala = False
estado_luz_quarto = False
estado_portao = False
estado_ventilador = False

mqtt = None

# Controle de alertas anteriores
alerta_temperatura_anterior = False
alerta_movimento_anterior = False
alerta_distancia_anterior = False



# Funcoes de leitura dos sensores

def ler_temperatura_umidade():

    try:
        dht_sensor.measure()

        temperatura = dht_sensor.temperature()
        umidade = dht_sensor.humidity()

        return temperatura, umidade

    except Exception as erro:
        print("Erro DHT22:", erro)
        return None, None




def ler_distancia():

    try:
        trig.value(0)
        time.sleep_us(2)

        trig.value(1)
        time.sleep_us(10)

        trig.value(0)

        duracao = time_pulse_us(echo, 1, 30000)

        distancia = (duracao * 0.0343) / 2

        return round(distancia, 2)

    except Exception as erro:
        print("Erro HC-SR04:", erro)
        return None



def ler_movimento():

    return pir.value()



def ler_luminosidade():

    return ldr.read()



def ler_sensores():

    temperatura, umidade = ler_temperatura_umidade()

    distancia = ler_distancia()

    movimento = ler_movimento()

    luminosidade = ler_luminosidade()

    return {
        "temperatura": temperatura,
        "umidade": umidade,
        "distancia": distancia,
        "movimento": movimento,
        "luminosidade": luminosidade
    }



# Funcoes de controle dos atuadores
def controlar_luz_sala(estado):

    global estado_luz_sala

    estado_luz_sala = bool(estado)

    led_sala.value(1 if estado_luz_sala else 0)

    print("Luz sala:", estado_luz_sala)


def controlar_luz_quarto(estado):

    global estado_luz_quarto

    estado_luz_quarto = bool(estado)

    led_quarto.value(1 if estado_luz_quarto else 0)

    print("Luz quarto:", estado_luz_quarto)


def controlar_portao(estado):

    global estado_portao

    estado_portao = bool(estado)

    # Servo fechado = 0 graus
    # Servo aberto = 90 graus

    angulo = 90 if estado_portao else 0

    pulso_us = 500 + (angulo / 180) * 2000

    servo.duty_ns(int(pulso_us * 1000))

    print("Portao:", "ABERTO" if estado_portao else "FECHADO")



def controlar_ventilador(estado):

    global estado_ventilador

    estado_ventilador = bool(estado)

    
    if estado_ventilador:
        buzzer.freq(1000)
        buzzer.duty_u16(16384)
    else:
        buzzer.duty_u16(0)

    print("Ventilador (buzzer):", "LIGADO" if estado_ventilador else "DESLIGADO")




# Controle automatico do ventilador por temperatura

def controlar_temperatura(temperatura):

    global modo_ventilador

    if temperatura is None:
        return

    if modo_ventilador == "AUTO":

        if temperatura >= TEMP_LIGAR_VENTILADOR:
            controlar_ventilador(True)

        elif temperatura <= TEMP_DESLIGAR_VENTILADOR:
            controlar_ventilador(False)




# Recebimento de comandos MQTT

def receber_mensagem_mqtt(topico, mensagem):

    global modo_ventilador

    topico = topico.decode()
    mensagem = mensagem.decode().strip().upper()

    print("MQTT recebido:", topico, mensagem)

    if topico == TOPICO_LUZ_SALA:

        controlar_luz_sala(mensagem == "ON")

    elif topico == TOPICO_LUZ_QUARTO:

        controlar_luz_quarto(mensagem == "ON")

    elif topico == TOPICO_PORTAO:

        if mensagem == "ABRIR":
            controlar_portao(True)

        elif mensagem == "FECHAR":
            controlar_portao(False)

    elif topico == TOPICO_VENTILADOR:

        if mensagem == "AUTO":

            modo_ventilador = "AUTO"
            print("Ventilador em modo automatico")

        elif mensagem == "ON":

            modo_ventilador = "ON"
            controlar_ventilador(True)

        elif mensagem == "OFF":

            modo_ventilador = "OFF"
            controlar_ventilador(False)




# Verificacao de alertas

def verificar_alertas(dados):

    global alerta_temperatura_anterior
    global alerta_movimento_anterior
    global alerta_distancia_anterior

    alertas = []

    temperatura = dados["temperatura"]
    movimento = dados["movimento"]
    distancia = dados["distancia"]

    # Alerta de temperatura elevada
    temperatura_alta = (
        temperatura is not None and temperatura >= TEMP_LIGAR_VENTILADOR
    )

    if temperatura_alta and not alerta_temperatura_anterior:

        alertas.append({
            "tipo": "temperatura_alta",
            "mensagem": "Temperatura elevada",
            "valor": temperatura
        })

    alerta_temperatura_anterior = temperatura_alta

    # Alerta de movimento
    movimento_detectado = movimento == 1

    if movimento_detectado and not alerta_movimento_anterior:

        alertas.append({
            "tipo": "movimento",
            "mensagem": "Movimento detectado",
            "valor": movimento
        })

    alerta_movimento_anterior = movimento_detectado

    # Alerta de proximidade
    distancia_baixa = (
        distancia is not None and distancia <= 20
    )

    if distancia_baixa and not alerta_distancia_anterior:

        alertas.append({
            "tipo": "proximidade",
            "mensagem": "Objeto proximo ao portao",
            "valor": distancia
        })

    alerta_distancia_anterior = distancia_baixa

    return alertas



# Atualizacao do display OLED
def atualizar_display(dados, status_mqtt):

    if display is None:
        return

    try:
        display.fill(0)

        temperatura = dados["temperatura"]
        umidade = dados["umidade"]
        distancia = dados["distancia"]
        movimento = dados["movimento"]

        display.text("SMART HOME - M2", 0, 0)
        display.text("Temp: {} C".format(temperatura if temperatura is not None else "--"), 0, 10)
        display.text("Umid: {} %".format(umidade if umidade is not None else "--"), 0, 20)
        display.text("Dist: {} cm".format(distancia if distancia is not None else "--"), 0, 30)
        display.text("Mov: {}".format("SIM" if movimento else "NAO"), 0, 40)
        display.text("Vent:{} MQTT:{}".format("ON" if estado_ventilador else "OFF", status_mqtt), 0, 50)

        display.show()

    except Exception as erro:
        print("Erro no OLED:", erro)




# Conexao Wi-Fi

def conectar_wifi():

    wlan = network.WLAN(network.STA_IF)

    wlan.active(True)

    if not wlan.isconnected():

        print("Conectando ao Wi-Fi...")

        wlan.connect(WIFI_SSID, WIFI_SENHA)

        while not wlan.isconnected():

            print(".", end="")

            time.sleep(0.5)

    print()
    print("Wi-Fi conectado!")
    print("IP:", wlan.ifconfig()[0])

    return wlan




# Conexao MQTT

def conectar_mqtt():

    try:

        cliente = MQTTClient(
            client_id=MQTT_CLIENT_ID,
            server=MQTT_BROKER,
            port=MQTT_PORTA,
            keepalive=60
        )

        cliente.set_callback(receber_mensagem_mqtt)

        cliente.connect()

        for topico in TOPICOS_CONTROLE:

            cliente.subscribe(topico)

            print("Inscrito:", topico)

        cliente.publish(TOPICO_STATUS, b"online", retain=True)

        print("MQTT conectado!")

        return cliente

    except Exception as erro:

        print("Erro MQTT:", erro)

        return None



# Publicacao dos dados via MQTT

def enviar_telemetria(dados):

    global mqtt

    if mqtt is None:
        return

    try:

        dados_envio = dict(dados)

        dados_envio["atuadores"] = {
            "luz_sala": estado_luz_sala,
            "luz_quarto": estado_luz_quarto,
            "portao": estado_portao,
            "ventilador": estado_ventilador,
            "modo_ventilador": modo_ventilador
        }

        mqtt.publish(
            TOPICO_TELEMETRIA,
            ujson.dumps(dados_envio)
        )

    except Exception as erro:

        print("Erro ao publicar telemetria:", erro)



# Envio dos alertas via MQTT

def enviar_alertas(alertas):

    global mqtt

    if mqtt is None:
        return

    for alerta in alertas:

        try:

            mqtt.publish(
                TOPICO_ALERTAS,
                ujson.dumps(alerta)
            )

            print("Alerta enviado:", alerta["mensagem"])

        except Exception as erro:

            print("Erro ao enviar alerta:", erro)






# Loop principal

def iniciar_sistema():

    global mqtt

    conectar_wifi()

    mqtt = conectar_mqtt()

    while True:

        try:

            # Verifica se existem comandos recebidos
            if mqtt is not None:
                mqtt.check_msg()

            # Leitura dos sensores
            dados = ler_sensores()

            # Controle automatico do ventilador
            controlar_temperatura(dados["temperatura"])

            # Verificacao dos alertas
            alertas = verificar_alertas(dados)

            # Atualizacao do OLED
            status_mqtt = "OK" if mqtt is not None else "OFF"

            atualizar_display(dados, status_mqtt)

            # Envio dos dados para o Node-RED
            enviar_telemetria(dados)

            # Envio dos alertas
            enviar_alertas(alertas)

            # Exibicao no terminal
            print("----------------------------------")
            print("Temperatura:", dados["temperatura"])
            print("Umidade:", dados["umidade"])
            print("Distancia:", dados["distancia"])
            print("Movimento:", dados["movimento"])
            print("Luminosidade:", dados["luminosidade"])
            print("Ventilador:", estado_ventilador)
            print("Modo:", modo_ventilador)

            gc.collect()

            # espera 5 s no total, mas verifica comandos MQTT a cada 0,5 s
            for _ in range(10):
                if mqtt is not None:
                    mqtt.check_msg()
                time.sleep(0.5)

        except Exception as erro:

            print("Erro no loop principal:", erro)

            time.sleep(2)


# Inicializacao

iniciar_sistema()