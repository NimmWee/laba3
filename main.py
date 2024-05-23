from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.templating import Jinja2Templates
import uvicorn
from fastapi.staticfiles import StaticFiles
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image
import requests

app = FastAPI()

# указываем папку с шаблонами
templates = Jinja2Templates(directory="templates")
# монтируем папку static
app.mount("/static", StaticFiles(directory="static"), name="static")

def add_gaussian_noise(image_bytes, noise_level):
    # Загрузить изображение из байтов
    image = Image.open(io.BytesIO(image_bytes))

    # Преобразовать изображение в массив numpy
    image_array = np.array(image)

    # Добавить гауссовский шум к изображению
    noisy_image_array = image_array + noise_level * np.random.randn(*image_array.shape)

    # Ограничить значения пикселей в диапазоне [0, 255]
    noisy_image_array = np.clip(noisy_image_array, 0, 255)

    # Преобразовать массив обратно в изображение
    noisy_image = Image.fromarray(np.uint8(noisy_image_array))

    # Сохранить изображение в байты
    noisy_image_bytes = io.BytesIO()
    noisy_image.save(noisy_image_bytes, format='PNG')
    noisy_image_bytes = noisy_image_bytes.getvalue()

    return noisy_image_bytes

def generate_color_histogram(image_bytes):
    # Загрузить изображение из байтов
    image = Image.open(io.BytesIO(image_bytes))

    # Преобразовать изображение в массив numpy
    img_array = np.array(image)

    # Создать гистограммы для каждого канала цвета
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.hist(img_array.ravel(), bins=256, range=(0, 256), color='r', alpha=0.5)
    ax1.set_title('Исходное изображение')
    ax1.set_xlabel('Значение пикселя')
    ax1.set_ylabel('Количество пикселей')

    ax2.hist(img_array.ravel(), bins=256, range=(0, 256), color='g', alpha=0.5)
    ax2.set_title('Изображение с шумом')
    ax2.set_xlabel('Значение пикселя')
    ax2.set_ylabel('Количество пикселей')

    # Сохраняем графики в байтовые строки
    histogram_bytes = io.BytesIO()
    plt.savefig(histogram_bytes, format='png')
    histogram_bytes.seek(0)

    return histogram_bytes.getvalue()

# возвращаем основной обработанный шаблон index.html
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add_noise")
async def add_noise(request: Request, file: UploadFile = File(...), noise_level: float = Form(0.5), resp: str = Form(...)):
    try:
        # Считываем файл изображения
        contents = await file.read()

        # Проверяем Captcha
        secret_key = "6LeQr-MpAAAAAHEriEy5jXJ5f-Fm2AAyLPcOHCXe"  # Замените на ваш секретный ключ
        payload = {
            "secret": secret_key,
            "response": resp
        }
        response = requests.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
        result = response.json()

        if result["success"]:
            # Добавляем шум к изображению
            noisy_image = add_gaussian_noise(contents, noise_level)

            # Генерируем гистограммы цветового распределения
            histogram = generate_color_histogram(noisy_image)

            # Кодируем изображения в base64 для отображения в шаблоне
            noisy_image_base64 = base64.b64encode(noisy_image).decode('utf-8')
            histogram_base64 = base64.b64encode(histogram).decode('utf-8')

            return templates.TemplateResponse("index.html", {"request": request, "noisy_image": noisy_image_base64, "histogram": histogram_base64})
        else:
            return templates.TemplateResponse("index.html", {"request": request, "error": "Captcha не пройдена"})

    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "detail": [{"type": "error", "msg": str(e)}]})

# запускаем локально веб сервер
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
