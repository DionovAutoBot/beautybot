import urllib.request
import ssl

def test_connection():
    print("🔍 Проверяю соединение с api.telegram.org...")
    
    # Создаём контекст, чтобы не ругался на сертификаты при тесте
    context = ssl.create_default_context()
    
    try:
        # Пытаемся "постучаться" на сервер Телеграма (таймаут 10 сек)
        response = urllib.request.urlopen('https://api.telegram.org', timeout=10, context=context)
        print(f"✅ УСПЕХ! Сервер ответил: {response.status}")
        print("👉 Проблема НЕ в сети. Скорее всего, дело в токене или коде бота.")
    except urllib.error.URLError as e:
        print(f"❌ Ошибка соединения: {e.reason}")
        print("👉 Проблема в сети: блокировка провайдера, фаервол или плохой интернет.")
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_connection()
    input("\nНажми Enter, чтобы выйти...")