import sys
import pandas as pd
import os
import json
import sqlite3

from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


@dataclass
class Product:
    name: str
    quantity: int
    price: float
    category: str
    sku: str


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect('organizations.db', check_same_thread=False)
        self.init_database()

    def init_database(self):
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                inn TEXT UNIQUE NOT NULL,
                address TEXT,
                phone TEXT,
                email TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                category TEXT,
                sku TEXT,
                FOREIGN KEY (org_id) REFERENCES organizations (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_org_id INTEGER,
                to_org_id INTEGER,
                product_name TEXT,
                quantity INTEGER,
                total_amount REAL,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                contract_path TEXT
            )
        ''')

        self.conn.commit()


class OrganizationManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
        self.load_initial_data()

    def init_ui(self):
        self.setWindowTitle("🏢 Organization Management System")
        self.setGeometry(100, 100, 1200, 800)

        # Центральный виджет с вкладками
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.create_dashboard_tab()
        self.create_organizations_tab()
        self.create_products_tab()
        self.create_transactions_tab()

        self.statusBar().showMessage("✅ Система готова к работе")

    def create_dashboard_tab(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("📊 Дашборд системы")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Метрики
        metrics_layout = QHBoxLayout()

        self.metric_orgs = self.create_metric_widget("🏢 Организации", "0")
        self.metric_products = self.create_metric_widget("📦 Товары", "0")
        self.metric_value = self.create_metric_widget("💰 Стоимость", "0 руб")
        self.metric_transactions = self.create_metric_widget("🔄 Транзакции", "0")

        metrics_layout.addWidget(self.metric_orgs)
        metrics_layout.addWidget(self.metric_products)
        metrics_layout.addWidget(self.metric_value)
        metrics_layout.addWidget(self.metric_transactions)

        layout.addLayout(metrics_layout)

        # Графики (упрощенные)
        charts_layout = QHBoxLayout()

        # Круговая диаграмма категорий
        self.category_chart_view = QChartView()
        charts_layout.addWidget(self.category_chart_view)

        # Гистограмма организаций
        self.orgs_chart_view = QChartView()
        charts_layout.addWidget(self.orgs_chart_view)

        layout.addLayout(charts_layout)

        dashboard_tab.setLayout(layout)
        self.tab_widget.addTab(dashboard_tab, "📊 Дашборд")

    def create_metric_widget(self, title, value):
        widget = QGroupBox(title)
        layout = QVBoxLayout()

        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2E86AB;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(value_label)
        widget.setLayout(layout)
        widget.setFixedSize(180, 80)

        return widget

    def create_organizations_tab(self):
        org_tab = QWidget()
        layout = QVBoxLayout()

        # Панель управления
        control_layout = QHBoxLayout()

        add_org_btn = QPushButton("🏢 Добавить организацию")
        add_org_btn.clicked.connect(self.add_organization)

        import_btn = QPushButton("📥 Импорт CSV")
        import_btn.clicked.connect(self.import_organization_csv)

        control_layout.addWidget(add_org_btn)
        control_layout.addWidget(import_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        # Таблица организаций
        self.orgs_table = QTableWidget()
        self.orgs_table.setColumnCount(5)
        self.orgs_table.setHorizontalHeaderLabels([
            "Название", "ИНН", "Адрес", "Телефон", "Товары"
        ])

        layout.addWidget(self.orgs_table)

        org_tab.setLayout(layout)
        self.tab_widget.addTab(org_tab, "🏢 Организации")

    def create_products_tab(self):
        products_tab = QWidget()
        layout = QVBoxLayout()

        # Фильтры
        filter_layout = QHBoxLayout()

        self.org_filter = QComboBox()
        self.org_filter.addItem("Все организации")
        self.org_filter.currentTextChanged.connect(self.filter_products)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск товаров...")
        self.search_input.textChanged.connect(self.filter_products)

        filter_layout.addWidget(QLabel("Организация:"))
        filter_layout.addWidget(self.org_filter)
        filter_layout.addWidget(self.search_input)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Таблица товаров
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels([
            "Организация", "Наименование", "Категория", "Кол-во", "Цена", "Стоимость"
        ])

        layout.addWidget(self.products_table)

        products_tab.setLayout(layout)
        self.tab_widget.addTab(products_tab, "📦 Товары")

    def create_transactions_tab(self):
        transactions_tab = QWidget()
        layout = QVBoxLayout()

        transfer_btn = QPushButton("🔄 Создать перемещение товаров")
        transfer_btn.clicked.connect(self.create_transfer)
        layout.addWidget(transfer_btn)

        # Таблица транзакций
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels([
            "Дата", "От", "Кому", "Товар", "Кол-во", "Сумма"
        ])

        layout.addWidget(self.transactions_table)

        transactions_tab.setLayout(layout)
        self.tab_widget.addTab(transactions_tab, "📋 Транзакции")

    def load_initial_data(self):
        self.update_dashboard()
        self.update_organizations_table()
        self.update_products_table()
        self.update_transactions_table()
        self.update_charts()

    def update_dashboard(self):
        cursor = self.db.conn.cursor()

        # Количество организаций
        cursor.execute("SELECT COUNT(*) FROM organizations")
        org_count = cursor.fetchone()[0]
        self.metric_orgs.layout().itemAt(0).widget().setText(str(org_count))

        # Общее количество товаров
        cursor.execute("SELECT SUM(quantity) FROM products")
        products_count = cursor.fetchone()[0] or 0
        self.metric_products.layout().itemAt(0).widget().setText(str(products_count))

        # Общая стоимость
        cursor.execute("SELECT SUM(quantity * price) FROM products")
        total_value = cursor.fetchone()[0] or 0
        self.metric_value.layout().itemAt(0).widget().setText(f"{total_value:,.0f} руб")

        # Количество транзакций
        cursor.execute("SELECT COUNT(*) FROM transactions")
        transactions_count = cursor.fetchone()[0]
        self.metric_transactions.layout().itemAt(0).widget().setText(str(transactions_count))

    def update_organizations_table(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT o.name, o.inn, o.address, o.phone, COUNT(p.id)
            FROM organizations o
            LEFT JOIN products p ON o.id = p.org_id
            GROUP BY o.id
        ''')

        organizations = cursor.fetchall()

        self.orgs_table.setRowCount(len(organizations))
        for row, org in enumerate(organizations):
            for col, value in enumerate(org):
                self.orgs_table.setItem(row, col, QTableWidgetItem(str(value)))

    def update_products_table(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT o.name, p.name, p.category, p.quantity, p.price, p.quantity * p.price
            FROM products p
            JOIN organizations o ON p.org_id = o.id
        ''')

        products = cursor.fetchall()

        self.products_table.setRowCount(len(products))
        for row, product in enumerate(products):
            for col, value in enumerate(product):
                item = QTableWidgetItem(str(value))
                if col in [3, 4, 5]:  # Числовые колонки
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.products_table.setItem(row, col, item)

    def update_transactions_table(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT t.transaction_date, o1.name, o2.name, t.product_name, t.quantity, t.total_amount
            FROM transactions t
            JOIN organizations o1 ON t.from_org_id = o1.id
            JOIN organizations o2 ON t.to_org_id = o2.id
            ORDER BY t.transaction_date DESC
        ''')

        transactions = cursor.fetchall()

        self.transactions_table.setRowCount(len(transactions))
        for row, transaction in enumerate(transactions):
            for col, value in enumerate(transaction):
                item = QTableWidgetItem(str(value))
                if col in [4, 5]:  # Числовые колонки
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.transactions_table.setItem(row, col, item)

    def update_charts(self):
        # Круговая диаграмма категорий
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT category, COUNT(*) 
            FROM products 
            WHERE category IS NOT NULL 
            GROUP BY category
        ''')

        category_data = cursor.fetchall()

        series = QPieSeries()
        for category, count in category_data:
            series.append(category, count)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Распределение по категориям")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)

        self.category_chart_view.setChart(chart)

    def add_organization(self):
        dialog = AddOrganizationDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_initial_data()

    def import_organization_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите CSV файл", "", "CSV Files (*.csv)")
        if file_path:
            try:
                df = pd.read_csv(file_path)
                QMessageBox.information(self, "Успех", f"Загружено {len(df)} записей")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {str(e)}")

    def create_transfer(self):
        dialog = TransferDialog(self, self.db)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_initial_data()


class AddOrganizationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить организацию")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.inn_input = QLineEdit()
        self.address_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()

        layout.addRow("Название*:", self.name_input)
        layout.addRow("ИНН*:", self.inn_input)
        layout.addRow("Адрес:", self.address_input)
        layout.addRow("Телефон:", self.phone_input)
        layout.addRow("Email:", self.email_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_organization)
        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)
        self.setLayout(layout)

    def save_organization(self):
        name = self.name_input.text().strip()
        inn = self.inn_input.text().strip()

        if not name or not inn:
            QMessageBox.warning(self, "Ошибка", "Поля 'Название' и 'ИНН' обязательны для заполнения")
            return

        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                INSERT INTO organizations (name, inn, address, phone, email)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, inn, self.address_input.text(), self.phone_input.text(), self.email_input.text()))

            self.db.conn.commit()
            QMessageBox.information(self, "Успех", "Организация добавлена")
            self.accept()

        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Ошибка", "Организация с таким названием или ИНН уже существует")


class TransferDialog(QDialog):
    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Перемещение товаров")
        self.setModal(True)
        self.init_ui()
        self.load_organizations()

    def init_ui(self):
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.from_org_combo = QComboBox()
        self.to_org_combo = QComboBox()
        self.product_combo = QComboBox()
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 10000)

        self.from_org_combo.currentTextChanged.connect(self.load_products)

        form_layout.addRow("От организации*:", self.from_org_combo)
        form_layout.addRow("К организации*:", self.to_org_combo)
        form_layout.addRow("Товар*:", self.product_combo)
        form_layout.addRow("Количество*:", self.quantity_spin)

        layout.addLayout(form_layout)

        self.preview_label = QLabel()
        layout.addWidget(self.preview_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.execute_transfer)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)
        self.setLayout(layout)

    def load_organizations(self):
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM organizations")
        organizations = [row[0] for row in cursor.fetchall()]

        self.from_org_combo.addItems(organizations)
        self.to_org_combo.addItems(organizations)

    def load_products(self):
        org_name = self.from_org_combo.currentText()
        if not org_name:
            return

        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT p.name, p.quantity, p.price 
            FROM products p 
            JOIN organizations o ON p.org_id = o.id 
            WHERE o.name = ?
        ''', (org_name,))

        products = cursor.fetchall()

        self.product_combo.clear()
        for product in products:
            self.product_combo.addItem(f"{product[0]} ({product[1]} шт. × {product[2]} руб.)", product)

    def execute_transfer(self):
        # Логика перемещения товаров
        pass


def main():
    app = QApplication(sys.argv)

    # Устанавливаем стиль
    app.setStyle('Fusion')

    window = OrganizationManager()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()