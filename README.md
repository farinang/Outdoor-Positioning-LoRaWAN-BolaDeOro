# Posicionamiento en exteriores utilizando LoRaWAN

Este proyecto tiene como objetivo recolectar datos LoRaWAN para el desarrollo de un sistema de **posicionamiento en exteriores** en una camaronera llamada **Bola de Oro**.

Los nodos LoRaWAN se encuentran instalados en tableros eléctricos distribuidos en las piscinas de la camaronera. Estos tableros son utilizados para el control y activación de **aireadores eléctricos**.

La información recibida por los gateways LoRaWAN permitirá registrar parámetros como RSSI, SNR y otros datos de radiofrecuencia, los cuales posteriormente podrán ser utilizados para desarrollar y evaluar algoritmos de posicionamiento.

---

## 1. Instalación de Visual Studio Code

Instalar Visual Studio Code desde su página oficial:

```text
https://code.visualstudio.com/
```

Una vez instalado, abrir Visual Studio Code.

---

## 2. Instalación de Python

Instalar Python 3.11 o superior desde su página oficial:

```text
https://www.python.org/downloads/
```

Durante la instalación, marcar la opción:

```text
Add Python to PATH
```

Verificar la versión instalada ejecutando:

```bash
python --version
```

Se debería mostrar una versión similar a:

```text
Python 3.11.x
```

o superior.

---

## 3. Instalación de Visual Studio Code

Instalar Visual Studio Code desde su página oficial:

```text
https://code.visualstudio.com/
```

Una vez instalado, abrir Visual Studio Code para continuar con la instalación de PlatformIO.

---

## 4. Creación del entorno virtual de Python

Abrir una terminal dentro de Visual Studio Code:

```text
Terminal → New Terminal
```

Desde la carpeta principal del proyecto, crear el entorno virtual ejecutando:

```bash
python -m venv $nombre_entorno$
```

Esto creará una carpeta llamada:

```text
$nombre_entorno$
```

Finalmente, se debe de *activar* el entorno virtual, ya sea por consola o a través de comandos rápidos de VSCode.

Cuando el entorno virtual esté activado, la terminal mostrará algo similar a:

```text
($nombre_entorno$)
```

---

## 5. Instalación de dependencias de Python

Con el entorno virtual activado, instalar las dependencias necesarias utilizando el archivo:

```text
requirements.txt
```

Ejecutar:

```bash
pip install -r requirements.txt
```

También se puede utilizar:

```bash
python -m pip install -r requirements.txt
```

Una vez finalizada la instalación, el entorno estará preparado para ejecutar los programas Python del proyecto.

---
