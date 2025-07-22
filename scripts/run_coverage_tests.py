#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов с детальным отчетом о покрытии
Цель: достичь 80%+ покрытия кода
"""
import subprocess
import sys
import os
import time
from pathlib import Path
from app.utils.subprocess_security import safe_subprocess_run, SubprocessSecurityError


def run_command(cmd, description):
    """Запускает команду и возвращает результат"""
    print(f"\n🔄 {description}")
    print(f"Команда: {' '.join(cmd)}")

    result = safe_subprocess_run(cmd, check=False)

    if result.returncode == 0:
        print(f"✅ {description} - УСПЕШНО")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - ОШИБКА")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)

    return result.returncode == 0


def main():
    """Основная функция"""
    print("🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ С ПОКРЫТИЕМ КОДА")
    print("=" * 60)

    # Переходим в директорию backend
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)

    # Проверяем наличие pytest
    if not run_command(
        [sys.executable, "-m", "pytest", "--version"], "Проверка pytest"
    ):
        print("❌ pytest не установлен. Устанавливаю...")
        if not run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "pytest",
                "pytest-cov",
                "pytest-asyncio",
            ],
            "Установка pytest",
        ):
            print("❌ Не удалось установить pytest")
            return 1

    # Очищаем предыдущие отчеты
    print("\n🧹 Очистка предыдущих отчетов...")
    for path in ["htmlcov", ".coverage", "coverage.xml"]:
        if os.path.exists(path):
            if os.path.isdir(path):
                import shutil

                shutil.rmtree(path)
            else:
                os.remove(path)

    # Запускаем тесты по категориям
    test_categories = [
        ("tests/test_simple.py", "Простые тесты"),
        ("tests/test_auth.py", "Тесты аутентификации"),
        ("tests/test_models.py", "Тесты моделей"),
        ("tests/test_api.py", "Тесты API"),
        ("tests/test_integration_api.py", "Интеграционные тесты API"),
        ("tests/test_database_comprehensive.py", "Комплексные тесты БД"),
        ("tests/test_security_comprehensive.py", "Комплексные тесты безопасности"),
        ("tests/test_performance_comprehensive.py", "Тесты производительности"),
        ("tests/test_mocks.py", "Тесты с моками"),
        ("tests/test_performance.py", "Базовые тесты производительности"),
    ]

    print("\n📊 ЗАПУСК ТЕСТОВ ПО КАТЕГОРИЯМ")
    print("-" * 40)

    total_passed = 0
    total_failed = 0

    for test_file, description in test_categories:
        if os.path.exists(test_file):
            print(f"\n🔍 {description}")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    test_file,
                    "-v",
                    "--tb=short",
                    "--disable-warnings",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"✅ {description} - ПРОЙДЕНЫ")
                # Подсчитываем количество пройденных тестов
                lines = result.stdout.split("\n")
                for line in lines:
                    if "passed" in line and "failed" not in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == "passed":
                                try:
                                    passed = int(parts[i - 1])
                                    total_passed += passed
                                except (ValueError, IndexError) as e:
                                    print(f"Warning: Could not parse test count: {e}")
                                    pass
            else:
                print(f"❌ {description} - ОШИБКИ")
                if result.stderr:
                    print(result.stderr[:500])  # Первые 500 символов ошибки
                total_failed += 1
        else:
            print(f"⚠️ {description} - ФАЙЛ НЕ НАЙДЕН: {test_file}")

    print(f"\n📈 ПРОМЕЖУТОЧНЫЕ РЕЗУЛЬТАТЫ:")
    print(f"Пройдено тестов: {total_passed}")
    print(f"Файлов с ошибками: {total_failed}")

    # Запускаем полный набор тестов с покрытием
    print("\n🎯 ЗАПУСК ПОЛНОГО НАБОРА ТЕСТОВ С ПОКРЫТИЕМ")
    print("=" * 50)

    coverage_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=80",
        "-v",
        "--tb=short",
        "--disable-warnings",
        "--maxfail=10",  # Останавливаемся после 10 ошибок
    ]

    print(f"Команда: {' '.join(coverage_cmd)}")

    start_time = time.time()
    result = subprocess.run(coverage_cmd, text=True)
    end_time = time.time()

    print(f"\n⏱️ Время выполнения: {end_time - start_time:.2f} секунд")

    if result.returncode == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Покрытие кода достигло 80%+")

        # Показываем информацию о покрытии
        if os.path.exists("htmlcov/index.html"):
            print(
                f"\n📊 HTML отчет о покрытии: {os.path.abspath('htmlcov/index.html')}"
            )

        if os.path.exists("coverage.xml"):
            print(f"📊 XML отчет о покрытии: {os.path.abspath('coverage.xml')}")

        print("\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ПОКРЫТИЯ:")

        # Запускаем детальный отчет о покрытии
        coverage_report_cmd = [
            sys.executable,
            "-m",
            "coverage",
            "report",
            "--show-missing",
        ]
        subprocess.run(coverage_report_cmd)

        return 0
    else:
        print("\n❌ ТЕСТЫ ЗАВЕРШИЛИСЬ С ОШИБКАМИ")

        if result.returncode == 1:
            print("⚠️ Некоторые тесты не прошли, но покрытие может быть достигнуто")
        elif result.returncode == 2:
            print("❌ Покрытие кода ниже 80%")

        # Показываем текущее покрытие
        print("\n📊 ТЕКУЩЕЕ ПОКРЫТИЕ:")
        coverage_report_cmd = [sys.executable, "-m", "coverage", "report"]
        subprocess.run(coverage_report_cmd)

        return 1


if __name__ == "__main__":
    sys.exit(main())
