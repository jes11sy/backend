#!/usr/bin/env python3
"""
Скрипт для запуска всех продвинутых типов тестов
E2E, Load Testing, Chaos Engineering, Contract Testing
"""
import asyncio
import subprocess
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
from datetime import datetime

# Добавляем путь к приложению
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.subprocess_security import safe_subprocess_run, SubprocessSecurityError


class AdvancedTestRunner:
    """Основной класс для запуска продвинутых тестов"""

    def __init__(self):
        self.results = {
            "start_time": None,
            "end_time": None,
            "total_duration": 0,
            "test_results": {},
        }

    def run_command(
        self, cmd: List[str], description: str, timeout: int = 300
    ) -> Dict[str, Any]:
        """Запуск команды с безопасностью и таймаутом"""
        print(f"\n🔄 {description}")
        print(f"Команда: {' '.join(cmd)}")

        start_time = time.time()

        try:
            result = safe_subprocess_run(cmd, timeout=timeout, check=False)
            duration = time.time() - start_time

            success = result.returncode == 0

            if success:
                print(f"✅ {description} - УСПЕШНО ({duration:.2f}s)")
            else:
                print(f"❌ {description} - ОШИБКА ({duration:.2f}s)")
                if result.stderr:
                    print(f"Ошибка: {result.stderr[:500]}")

            return {
                "success": success,
                "duration": duration,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except SubprocessSecurityError as e:
            print(f"🔒 {description} - БЛОКИРОВАНО ПО БЕЗОПАСНОСТИ: {e}")
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

        except Exception as e:
            print(f"💥 {description} - КРИТИЧЕСКАЯ ОШИБКА: {e}")
            return {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    def run_e2e_tests(self) -> Dict[str, Any]:
        """Запуск E2E тестов"""
        print("\n" + "=" * 60)
        print("🎯 ЗАПУСК E2E ТЕСТОВ")
        print("=" * 60)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_e2e_scenarios.py",
            "-v",
            "--tb=short",
            "--disable-warnings",
            "--asyncio-mode=auto",
            "--maxfail=5",
        ]

        result = self.run_command(
            cmd, "E2E тесты пользовательских сценариев", timeout=600
        )

        # Анализируем результаты
        if result["success"]:
            # Подсчитываем количество пройденных тестов
            stdout = result.get("stdout", "")
            if "passed" in stdout:
                print("📊 E2E тесты показали хорошие результаты")
            else:
                print("⚠️ E2E тесты завершились, но результаты неясны")
        else:
            print("❌ E2E тесты не прошли")

        return result

    def run_load_tests(self) -> Dict[str, Any]:
        """Запуск Load тестов"""
        print("\n" + "=" * 60)
        print("⚡ ЗАПУСК LOAD ТЕСТОВ")
        print("=" * 60)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_load_testing.py",
            "-v",
            "--tb=short",
            "--disable-warnings",
            "--asyncio-mode=auto",
            "-s",  # Показывать print statements
        ]

        result = self.run_command(cmd, "Load тесты производительности", timeout=900)

        # Анализируем результаты нагрузочного тестирования
        if result["success"]:
            stdout = result.get("stdout", "")
            if "Load Test Results" in stdout:
                print("📈 Load тесты показали метрики производительности")
            else:
                print("⚠️ Load тесты завершились без детальных метрик")
        else:
            print("❌ Load тесты выявили проблемы с производительностью")

        return result

    def run_chaos_tests(self) -> Dict[str, Any]:
        """Запуск Chaos Engineering тестов"""
        print("\n" + "=" * 60)
        print("🔥 ЗАПУСК CHAOS ENGINEERING ТЕСТОВ")
        print("=" * 60)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_chaos_engineering.py",
            "-v",
            "--tb=short",
            "--disable-warnings",
            "--asyncio-mode=auto",
            "-s",  # Показывать print statements
        ]

        result = self.run_command(
            cmd, "Chaos Engineering тесты отказоустойчивости", timeout=800
        )

        # Анализируем результаты chaos testing
        if result["success"]:
            stdout = result.get("stdout", "")
            if "chaos scenario" in stdout.lower():
                print("🛡️ Chaos тесты проверили отказоустойчивость системы")
            else:
                print("⚠️ Chaos тесты завершились без детального анализа")
        else:
            print("❌ Chaos тесты выявили проблемы с отказоустойчивостью")

        return result

    def run_contract_tests(self) -> Dict[str, Any]:
        """Запуск Contract тестов"""
        print("\n" + "=" * 60)
        print("📋 ЗАПУСК CONTRACT ТЕСТОВ")
        print("=" * 60)

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_contract_testing.py",
            "-v",
            "--tb=short",
            "--disable-warnings",
            "--asyncio-mode=auto",
        ]

        result = self.run_command(cmd, "Contract тесты API контрактов", timeout=400)

        # Анализируем результаты contract testing
        if result["success"]:
            stdout = result.get("stdout", "")
            if "contract" in stdout.lower():
                print("📄 Contract тесты проверили соответствие API контрактам")
            else:
                print("⚠️ Contract тесты завершились без детального анализа")
        else:
            print("❌ Contract тесты выявили несоответствия API контрактам")

        return result

    def run_all_tests(self, test_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Запуск всех или выбранных типов тестов"""
        if test_types is None:
            test_types = ["e2e", "load", "chaos", "contract"]

        self.results["start_time"] = datetime.now().isoformat()
        start_time = time.time()

        print("🚀 ЗАПУСК ПРОДВИНУТЫХ ТЕСТОВ")
        print(f"Выбранные типы тестов: {', '.join(test_types)}")
        print(f"Время начала: {self.results['start_time']}")

        # Запускаем выбранные типы тестов
        if "e2e" in test_types:
            self.results["test_results"]["e2e"] = self.run_e2e_tests()

        if "load" in test_types:
            self.results["test_results"]["load"] = self.run_load_tests()

        if "chaos" in test_types:
            self.results["test_results"]["chaos"] = self.run_chaos_tests()

        if "contract" in test_types:
            self.results["test_results"]["contract"] = self.run_contract_tests()

        # Финализируем результаты
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_duration"] = time.time() - start_time

        return self.results

    def generate_report(self) -> str:
        """Генерация отчета о тестировании"""
        report = []
        report.append("=" * 80)
        report.append("📊 ОТЧЕТ О ПРОДВИНУТОМ ТЕСТИРОВАНИИ")
        report.append("=" * 80)

        report.append(f"🕐 Время начала: {self.results['start_time']}")
        report.append(f"🕐 Время окончания: {self.results['end_time']}")
        report.append(
            f"⏱️ Общая продолжительность: {self.results['total_duration']:.2f} секунд"
        )

        report.append("\n📋 РЕЗУЛЬТАТЫ ПО ТИПАМ ТЕСТОВ:")
        report.append("-" * 50)

        total_tests = len(self.results["test_results"])
        passed_tests = 0

        for test_type, result in self.results["test_results"].items():
            status = "✅ ПРОШЕЛ" if result["success"] else "❌ НЕ ПРОШЕЛ"
            duration = result["duration"]

            report.append(f"{test_type.upper():12} | {status} | {duration:8.2f}s")

            if result["success"]:
                passed_tests += 1

            # Добавляем детали ошибок
            if not result["success"] and "error" in result:
                report.append(f"             Ошибка: {result['error']}")

        report.append("-" * 50)
        report.append(f"ИТОГО: {passed_tests}/{total_tests} тестов прошли успешно")

        # Общая оценка
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        if success_rate >= 0.8:
            report.append(
                "\n🎉 ОТЛИЧНО! Система показала высокую готовность к production"
            )
        elif success_rate >= 0.6:
            report.append(
                "\n⚠️ ХОРОШО! Система в основном готова, но есть области для улучшения"
            )
        elif success_rate >= 0.4:
            report.append(
                "\n🔧 ТРЕБУЕТСЯ РАБОТА! Система нуждается в серьезных доработках"
            )
        else:
            report.append("\n🚨 КРИТИЧНО! Система не готова к production")

        report.append("\n" + "=" * 80)

        return "\n".join(report)

    def save_report(self, filename: Optional[str] = None):
        """Сохранение отчета в файл"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"advanced_test_report_{timestamp}.txt"

        report_content = self.generate_report()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_content)

        print(f"\n📄 Отчет сохранен в файл: {filename}")

        # Также сохраняем JSON данные
        json_filename = filename.replace(".txt", ".json")
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"📄 JSON данные сохранены в файл: {json_filename}")


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Запуск продвинутых тестов")
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["e2e", "load", "chaos", "contract"],
        default=["e2e", "load", "chaos", "contract"],
        help="Типы тестов для запуска",
    )
    parser.add_argument(
        "--report", default="advanced_test_report.txt", help="Имя файла отчета"
    )
    parser.add_argument(
        "--no-report", action="store_true", help="Не сохранять отчет в файл"
    )

    args = parser.parse_args()

    # Создаем runner и запускаем тесты
    runner = AdvancedTestRunner()

    try:
        results = runner.run_all_tests(args.types)

        # Выводим отчет
        report = runner.generate_report()
        print(report)

        # Сохраняем отчет
        if not args.no_report:
            runner.save_report(args.report)

        # Возвращаем код выхода
        total_tests = len(results["test_results"])
        passed_tests = sum(1 for r in results["test_results"].values() if r["success"])

        if passed_tests == total_tests:
            print("\n🎉 Все тесты прошли успешно!")
            sys.exit(0)
        elif passed_tests >= total_tests * 0.8:
            print("\n⚠️ Большинство тестов прошли, но есть проблемы")
            sys.exit(1)
        else:
            print("\n❌ Много тестов не прошли, требуется серьезная доработка")
            sys.exit(2)

    except KeyboardInterrupt:
        print("\n🛑 Тестирование прервано пользователем")
        sys.exit(130)

    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


def run_quick_test():
    """Быстрый тест для проверки работоспособности"""
    print("🚀 БЫСТРЫЙ ТЕСТ ПРОДВИНУТЫХ ВОЗМОЖНОСТЕЙ")

    runner = AdvancedTestRunner()

    # Запускаем только E2E тесты для быстрой проверки
    results = runner.run_all_tests(["e2e"])

    report = runner.generate_report()
    print(report)

    return results["test_results"]["e2e"]["success"]


if __name__ == "__main__":
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        success = run_quick_test()
        sys.exit(0 if success else 1)
    else:
        main()
