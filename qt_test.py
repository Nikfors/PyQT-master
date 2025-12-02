import sys
import pandas as pd
import os
import sqlite3
import time
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


class SplashScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Загрузка системы")
        self.setFixedSize(600, 400)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)

        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        layout = QVBoxLayout()

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap("1с.png")
        pixmap = pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(pixmap)

        # Статус загрузки
        self.status_label = QLabel("Инициализация системы...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #FFD700; margin: 10px;")

        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        layout.addWidget(self.logo_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(layout)
        container.setStyleSheet("background: #FFD700; border-radius: 10px;")
        self.setLayout(layout)

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        QApplication.processEvents()


def pre_start():
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()

    steps = [
        (10, "Загрузка ядра системы..."),
        (25, "Инициализация базы данных..."),
        (40, "Загрузка модулей интерфейса..."),
        (60, "Настройка компонентов..."),
        (80, "Подготовка данных..."),
        (95, "Запуск приложения..."),
        (100, "Готово!")
    ]

    for progress, message in steps:
        splash.update_progress(progress, message)
        time.sleep(0.5)

    main_window = OrganizationManager()
    splash.finish(main_window)
    main_window.show()
    return app.exec()


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
        self.setWindowTitle("🏢 Organization Management System")
        self.setGeometry(100, 100, 1200, 800)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.create_tabs()
        self.load_all_data()
        self.statusBar().showMessage("✅ Система готова к работе")

    def create_tabs(self):
        # Вкладка дашборда
        dashboard_tab = QWidget()
        layout = QVBoxLayout()

        title = QLabel("📊 Дашборд системы")
        title.setStyleSheet("font-size: 20pt; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Метрики
        metrics_layout = QHBoxLayout()
        self.metric_orgs = self.create_metric_widget("🏢 Организации", "0")
        self.metric_products = self.create_metric_widget("📦 Товары", "0")
        self.metric_value = self.create_metric_widget("💰 Стоимость", "0 руб")
        self.metric_transactions = self.create_metric_widget("🔄 Транзакции", "0")

        for metric in [self.metric_orgs, self.metric_products, self.metric_value, self.metric_transactions]:
            metrics_layout.addWidget(metric)
        layout.addLayout(metrics_layout)

        # Статистика
        stats_layout = QHBoxLayout()
        self.top_products_list = QListWidget()
        self.recent_transactions_list = QListWidget()

        left_panel = QGroupBox("🏆 Топ товаров по стоимости")
        left_panel.setLayout(QVBoxLayout())
        left_panel.layout().addWidget(self.top_products_list)

        right_panel = QGroupBox("📋 Последние операции")
        right_panel.setLayout(QVBoxLayout())
        right_panel.layout().addWidget(self.recent_transactions_list)

        stats_layout.addWidget(left_panel)
        stats_layout.addWidget(right_panel)
        layout.addLayout(stats_layout)
        dashboard_tab.setLayout(layout)

        # Вкладка организаций
        org_tab = QWidget()
        org_layout = QVBoxLayout()

        control_layout = QHBoxLayout()
        add_org_btn = QPushButton("🏢 Добавить организацию")
        add_org_btn.clicked.connect(self.add_organization)
        import_btn = QPushButton("📥 Импорт CSV")
        import_btn.clicked.connect(self.import_organization_csv)
        export_btn = QPushButton("📤 Экспорт в Excel")
        export_btn.clicked.connect(self.export_organizations)

        control_layout.addWidget(add_org_btn)
        control_layout.addWidget(import_btn)
        control_layout.addWidget(export_btn)
        control_layout.addStretch()
        org_layout.addLayout(control_layout)

        self.orgs_table = QTableWidget()
        self.orgs_table.setColumnCount(6)
        self.orgs_table.setHorizontalHeaderLabels(["ID", "Название", "ИНН", "Адрес", "Телефон", "Товары"])
        self.orgs_table.doubleClicked.connect(self.show_organization_details)
        org_layout.addWidget(self.orgs_table)
        org_tab.setLayout(org_layout)

        # Вкладка товаров
        products_tab = QWidget()
        products_layout = QVBoxLayout()

        filter_layout = QHBoxLayout()
        self.org_filter = QComboBox()
        self.org_filter.addItem("Все организации")
        self.category_filter = QComboBox()
        self.category_filter.addItem("Все категории")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск товаров...")

        for widget, label in [(self.org_filter, "Организация:"), (self.category_filter, "Категория:"),
                              (self.search_input, "")]:
            if label: filter_layout.addWidget(QLabel(label))
            filter_layout.addWidget(widget)

        self.org_filter.currentTextChanged.connect(self.filter_products)
        self.category_filter.currentTextChanged.connect(self.filter_products)
        self.search_input.textChanged.connect(self.filter_products)

        add_product_btn = QPushButton("➕ Добавить товар")
        add_product_btn.clicked.connect(self.add_product)
        filter_layout.addWidget(add_product_btn)
        products_layout.addLayout(filter_layout)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(7)
        self.products_table.setHorizontalHeaderLabels(
            ["ID", "Организация", "Наименование", "Категория", "Кол-во", "Цена", "Стоимость"])
        products_layout.addWidget(self.products_table)
        products_tab.setLayout(products_layout)

        # Вкладка транзакций
        transactions_tab = QWidget()
        transactions_layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        transfer_btn = QPushButton("🔄 Создать перемещение")
        transfer_btn.clicked.connect(self.create_transfer)
        generate_pdf_btn = QPushButton("📄 Создать отчет PDF")
        generate_pdf_btn.clicked.connect(self.generate_transactions_report)

        button_layout.addWidget(transfer_btn)
        button_layout.addWidget(generate_pdf_btn)
        button_layout.addStretch()
        transactions_layout.addLayout(button_layout)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(8)
        self.transactions_table.setHorizontalHeaderLabels(
            ["ID", "Дата", "От", "Кому", "Товар", "Кол-во", "Сумма", "Договор"])
        self.transactions_table.doubleClicked.connect(self.open_contract)
        transactions_layout.addWidget(self.transactions_table)
        transactions_tab.setLayout(transactions_layout)

        self.tab_widget.addTab(dashboard_tab, "📊 Дашборд")
        self.tab_widget.addTab(org_tab, "🏢 Организации")
        self.tab_widget.addTab(products_tab, "📦 Товары")
        self.tab_widget.addTab(transactions_tab, "📋 Транзакции")

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

    def load_all_data(self):
        self.update_dashboard()
        self.update_organizations_table()
        self.update_products_table()
        self.update_transactions_table()
        self.update_filters()

    def update_dashboard(self):
        cursor = self.db.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM organizations")
        org_count = cursor.fetchone()[0]
        self.update_metric_value(self.metric_orgs, str(org_count))

        cursor.execute("SELECT SUM(quantity) FROM products")
        products_count = cursor.fetchone()[0] or 0
        self.update_metric_value(self.metric_products, str(products_count))

        cursor.execute("SELECT SUM(quantity * price) FROM products")
        total_value = cursor.fetchone()[0] or 0
        self.update_metric_value(self.metric_value, f"{total_value:,.0f} руб")

        cursor.execute("SELECT COUNT(*) FROM transactions")
        transactions_count = cursor.fetchone()[0]
        self.update_metric_value(self.metric_transactions, str(transactions_count))

        cursor.execute('''
            SELECT p.name, o.name, p.quantity * p.price as total_value
            FROM products p JOIN organizations o ON p.org_id = o.id
            ORDER BY total_value DESC LIMIT 10
        ''')
        self.top_products_list.clear()
        for product in cursor.fetchall():
            self.top_products_list.addItem(f"{product[0]} ({product[1]}) - {product[2]:,.0f} руб")

        cursor.execute('''
            SELECT t.transaction_date, o1.name, o2.name, t.product_name, t.quantity
            FROM transactions t
            JOIN organizations o1 ON t.from_org_id = o1.id
            JOIN organizations o2 ON t.to_org_id = o2.id
            ORDER BY t.transaction_date DESC LIMIT 10
        ''')
        self.recent_transactions_list.clear()
        for transaction in cursor.fetchall():
            self.recent_transactions_list.addItem(f"{transaction[0][:16]}: {transaction[3]} ({transaction[4]} шт.)")

    def update_metric_value(self, metric_widget, value):
        metric_widget.layout().itemAt(0).widget().setText(value)

    def update_organizations_table(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT o.id, o.name, o.inn, o.address, o.phone, COUNT(p.id)
            FROM organizations o LEFT JOIN products p ON o.id = p.org_id
            GROUP BY o.id
        ''')
        self.fill_table(self.orgs_table, cursor.fetchall())

    def update_products_table(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT p.id, o.name, p.name, p.category, p.quantity, p.price, p.quantity * p.price
            FROM products p JOIN organizations o ON p.org_id = o.id
        ''')
        self.fill_table(self.products_table, cursor.fetchall(), [5, 6])

    def update_transactions_table(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT t.id, t.transaction_date, o1.name, o2.name, t.product_name, 
                   t.quantity, t.total_amount, t.contract_path
            FROM transactions t
            JOIN organizations o1 ON t.from_org_id = o1.id
            JOIN organizations o2 ON t.to_org_id = o2.id
            ORDER BY t.transaction_date DESC
        ''')
        self.fill_table(self.transactions_table, cursor.fetchall(), [5, 6])

    def fill_table(self, table, data, money_columns=None):
        table.setRowCount(len(data))
        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif col in (money_columns or []):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    try:
                        item.setText(f"{float(value):,.0f}" if value else "0")
                    except:
                        pass
                table.setItem(row, col, item)
        table.resizeColumnsToContents()

    def update_filters(self):
        cursor = self.db.conn.cursor()

        cursor.execute("SELECT name FROM organizations")
        orgs = [row[0] for row in cursor.fetchall()]
        self.update_combo(self.org_filter, orgs)

        cursor.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL")
        categories = [row[0] for row in cursor.fetchall()]
        self.update_combo(self.category_filter, categories)

    def update_combo(self, combo, items):
        current = combo.currentText()
        combo.clear()
        combo.addItem(f"Все {combo == self.org_filter and 'организации' or 'категории'}")
        combo.addItems(items)
        if current in items:
            combo.setCurrentText(current)

    def filter_products(self):
        try:
            query = '''
                SELECT p.id, o.name, p.name, p.category, p.quantity, p.price, p.quantity * p.price
                FROM products p JOIN organizations o ON p.org_id = o.id WHERE 1=1
            '''
            org_filter = self.org_filter.currentText()
            if org_filter != "Все организации":
                query += f" AND o.name = '{org_filter}'"

            category_filter = self.category_filter.currentText()
            if category_filter != "Все категории":
                query += f" AND p.category = '{category_filter}'"

            search_text = self.search_input.text().strip()
            if search_text:
                query += f" AND (p.name LIKE '%{search_text}%' OR p.category LIKE '%{search_text}%' OR p.sku LIKE '%{search_text}%')"

            cursor = self.db.conn.cursor()
            cursor.execute(query)
            self.fill_table(self.products_table, cursor.fetchall(), [5, 6])
        except Exception as e:
            print(f"Ошибка фильтрации: {e}")

    def add_organization(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить организацию")
        layout = QFormLayout()

        fields = {}
        for field in ["Название*:", "ИНН*:", "Адрес:", "Телефон:", "Email:"]:
            fields[field] = QLineEdit()
            layout.addRow(field, fields[field])

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(lambda: self.save_organization(dialog, fields))
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        dialog.setLayout(layout)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_all_data()
            QMessageBox.information(self, "Успех", "Организация успешно добавлена!")

    def save_organization(self, dialog, fields):
        name = fields["Название*:"].text().strip()
        inn = fields["ИНН*:"].text().strip()

        if not name or not inn:
            QMessageBox.warning(dialog, "Ошибка", "Поля 'Название' и 'ИНН' обязательны")
            return

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(f'''
                INSERT INTO organizations (name, inn, address, phone, email)
                VALUES ('{name}', '{inn}', '{fields["Адрес:"].text().strip()}', 
                        '{fields["Телефон:"].text().strip()}', '{fields["Email:"].text().strip()}')
            ''')
            self.db.conn.commit()
            dialog.accept()
        except sqlite3.IntegrityError:
            QMessageBox.critical(dialog, "Ошибка", "Организация с таким названием или ИНН уже существует")
        except Exception as e:
            QMessageBox.critical(dialog, "Ошибка", f"Ошибка базы данных: {str(e)}")

    def show_organization_details(self, index):
        row = index.row()
        org_id = self.orgs_table.item(row, 0).text()
        org_name = self.orgs_table.item(row, 1).text()

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Детали организации: {org_name}")
        dialog.resize(600, 400)

        layout = QVBoxLayout()

        # Информация об организации
        info_group = QGroupBox("Информация об организации")
        info_layout = QFormLayout()

        cursor = self.db.conn.cursor()
        cursor.execute(f'SELECT name, inn, address, phone, email, created_date FROM organizations WHERE id = {org_id}')
        org_data = cursor.fetchone()

        for label, value in [("Название:", org_data[0]), ("ИНН:", org_data[1]), ("Адрес:", org_data[2] or "Не указан"),
                             ("Телефон:", org_data[3] or "Не указан"), ("Email:", org_data[4] or "Не указан"),
                             ("Дата создания:", org_data[5])]:
            info_layout.addRow(label, QLabel(str(value)))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Товары организации
        products_group = QGroupBox("Товары на складе")
        products_table = QTableWidget()
        products_table.setColumnCount(4)
        products_table.setHorizontalHeaderLabels(["Товар", "Категория", "Кол-во", "Цена"])

        cursor.execute(f'SELECT name, category, quantity, price FROM products WHERE org_id = {org_id}')
        products = cursor.fetchall()
        products_table.setRowCount(len(products))

        for row, product in enumerate(products):
            for col, value in enumerate(product):
                item = QTableWidgetItem(str(value))
                if col in [2, 3]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 3:
                    try:
                        item.setText(f"{float(value):,.0f} руб")
                    except:
                        pass
                products_table.setItem(row, col, item)

        products_table.resizeColumnsToContents()
        products_group.setLayout(QVBoxLayout())
        products_group.layout().addWidget(products_table)
        layout.addWidget(products_group)

        dialog.setLayout(layout)
        dialog.exec()

    def add_product(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить товар")
        layout = QFormLayout()

        org_combo = QComboBox()
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name FROM organizations")
        for org_id, org_name in cursor.fetchall():
            org_combo.addItem(org_name, org_id)

        fields = {}
        for field in ["Наименование*:", "Категория:", "Артикул:"]:
            fields[field] = QLineEdit()
            layout.addRow(field, fields[field])

        quantity_spin = QSpinBox()
        quantity_spin.setRange(0, 100000)
        quantity_spin.setValue(1)
        layout.addRow("Количество*:", quantity_spin)

        price_spin = QDoubleSpinBox()
        price_spin.setRange(0, 1000000)
        price_spin.setDecimals(2)
        price_spin.setValue(0)
        price_spin.setPrefix("₽ ")
        layout.addRow("Цена*:", price_spin)

        layout.addRow("Организация*:", org_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(lambda: self.save_product(dialog, org_combo, fields, quantity_spin, price_spin))
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        dialog.setLayout(layout)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_all_data()
            QMessageBox.information(self, "Успех", "Товар успешно добавлен!")

    def save_product(self, dialog, org_combo, fields, quantity_spin, price_spin):
        org_id = org_combo.currentData()
        name = fields["Наименование*:"].text().strip()
        quantity = quantity_spin.value()
        price = price_spin.value()

        if not org_id or not name:
            QMessageBox.warning(dialog, "Ошибка", "Поля 'Организация' и 'Наименование' обязательны")
            return

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(f'''
                INSERT INTO products (org_id, name, quantity, price, category, sku)
                VALUES ({org_id}, '{name}', {quantity}, {price}, 
                        '{fields["Категория:"].text().strip()}', '{fields["Артикул:"].text().strip()}')
            ''')
            self.db.conn.commit()
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(dialog, "Ошибка", f"Ошибка при сохранении товара: {str(e)}")

    def create_transfer(self):
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name FROM organizations")
        organizations = cursor.fetchall()

        if len(organizations) < 2:
            QMessageBox.warning(self, "Ошибка", "Для перемещения нужно как минимум 2 организации")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Перемещение товаров")
        dialog.resize(500, 400)
        layout = QVBoxLayout()

        form_layout = QFormLayout()
        from_org_combo = QComboBox()
        to_org_combo = QComboBox()
        product_combo = QComboBox()
        quantity_spin = QSpinBox()
        quantity_spin.setRange(1, 10000)

        for org_id, org_name in organizations:
            from_org_combo.addItem(org_name, org_id)
            to_org_combo.addItem(org_name, org_id)

        form_layout.addRow("От организации*:", from_org_combo)
        form_layout.addRow("К организации*:", to_org_combo)
        form_layout.addRow("Товар*:", product_combo)
        form_layout.addRow("Количество*:", quantity_spin)
        layout.addLayout(form_layout)

        preview_label = QLabel("Выберите организации и товар для просмотра деталей")
        preview_label.setWordWrap(True)
        layout.addWidget(preview_label)

        def load_products():
            from_org_id = from_org_combo.currentData()
            if not from_org_id: return

            cursor.execute(
                f'SELECT id, name, quantity, price FROM products WHERE org_id = {from_org_id} AND quantity > 0')
            product_combo.clear()
            for product_id, name, quantity, price in cursor.fetchall():
                product_combo.addItem(f"{name} (доступно: {quantity} шт., цена: {price:,.0f} руб.)",
                                      (product_id, name, quantity, price))

        def update_preview():
            from_org = from_org_combo.currentText()
            to_org = to_org_combo.currentText()
            product_data = product_combo.currentData()
            quantity = quantity_spin.value()

            if from_org and to_org and product_data:
                product_id, product_name, available, price = product_data
                total_cost = quantity * price
                preview_text = f"""<b>Детали операции:</b><br>• <b>От:</b> {from_org}<br>• <b>К:</b> {to_org}<br>• 
                <b>Товар:</b> {product_name}<br>• <b>Количество:</b> {quantity} шт.<br>• 
                <b>Цена за единицу:</b> {price:,.0f} руб.<br>• <b>Общая стоимость:</b> 
                <span style='color: green;'>{total_cost:,.0f} руб.</span><br>• 
                <b>Доступно на складе:</b> {available} шт."""
                if quantity > available:
                    preview_text += (f"<br><span style='color: red;'>"
                                     f"<b>Внимание:</b> Запрашиваемое количество превышает доступное!</span>")
                preview_label.setText(preview_text)

        from_org_combo.currentTextChanged.connect(load_products)
        product_combo.currentTextChanged.connect(update_preview)
        quantity_spin.valueChanged.connect(update_preview)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(
            lambda: self.execute_transfer(dialog, from_org_combo, to_org_combo, product_combo, quantity_spin))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)
        dialog.exec()

    def execute_transfer(self, dialog, from_org_combo, to_org_combo, product_combo, quantity_spin):
        from_org_id = from_org_combo.currentData()
        to_org_id = to_org_combo.currentData()
        product_data = product_combo.currentData()
        quantity = quantity_spin.value()

        if not all([from_org_id, to_org_id, product_data]):
            QMessageBox.warning(dialog, "Ошибка", "Заполните все обязательные поля")
            return

        if from_org_id == to_org_id:
            QMessageBox.warning(dialog, "Ошибка", "Нельзя перемещать товар в ту же организацию")
            return

        product_id, product_name, available, price = product_data

        if quantity > available:
            QMessageBox.warning(dialog, "Ошибка", "Запрашиваемое количество превышает доступное на складе")
            return

        try:
            cursor = self.db.conn.cursor()

            # Уменьшаем количество у отправителя
            cursor.execute(
                f"UPDATE products SET quantity = quantity - {quantity} WHERE id = {product_id} AND quantity >= {quantity}")

            if cursor.rowcount == 0:
                raise Exception("Недостаточно товара на складе")

            # Проверяем, есть ли такой товар у получателя
            cursor.execute(f'SELECT id FROM products WHERE org_id = {to_org_id} AND name = ?', (product_name,))
            existing_product = cursor.fetchone()

            if existing_product:
                # Увеличиваем количество у получателя
                cursor.execute(f'UPDATE products SET quantity = quantity + {quantity} WHERE id = {existing_product[0]}')
            else:
                # Создаем новый товар у получателя
                cursor.execute(f'''
                    INSERT INTO products (org_id, name, quantity, price, category) 
                    SELECT {to_org_id}, name, {quantity}, price, category 
                    FROM products WHERE id = {product_id}
                ''')

            total_amount = quantity * price
            contract_path = self.generate_contract(from_org_combo.currentText(), to_org_combo.currentText(),
                                                   product_name, quantity, price, total_amount)

            # Исправленный INSERT с параметрами
            cursor.execute('''
                INSERT INTO transactions (from_org_id, to_org_id, product_name, quantity, total_amount, contract_path) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (from_org_id, to_org_id, product_name, quantity, total_amount, contract_path))

            self.db.conn.commit()
            QMessageBox.information(dialog, "Успех",
                                    f"Товар '{product_name}' в количестве {quantity} шт. успешно перемещен!"
                                    f"\nСоздан договор: {os.path.basename(contract_path)}")
            self.load_all_data()
            dialog.accept()

        except Exception as e:
            self.db.conn.rollback()
            QMessageBox.critical(dialog, "Ошибка", f"Ошибка при перемещении: {str(e)}")

    def generate_contract(self, from_org, to_org, product_name, quantity, price, total_amount):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"contract_{from_org}_{to_org}_{timestamp}.pdf"

        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Английский текст для PDF
        story.append(Paragraph("SALES CONTRACT", styles['Title']))
        story.append(Paragraph("<br/>", styles['Normal']))

        content = f"""
        <b>Document Date:</b> {datetime.now().strftime('%d.%m.%Y')}<br/>
        <b>Seller:</b> {from_org}<br/>
        <b>Buyer:</b> {to_org}<br/>
        <br/>
        <b>SUBJECT OF THE CONTRACT:</b><br/>
        Product Name: {product_name}<br/>
        Quantity: {quantity} units<br/>
        Price per unit: {price:,.0f} RUB<br/>
        Total amount: {total_amount:,.0f} RUB<br/>
        <br/>
        <b>TERMS AND CONDITIONS:</b><br/>
        1. The Seller undertakes to transfer the goods, the Buyer undertakes to accept and pay for them<br/>
        2. The goods shall be transferred within 3 business days<br/>
        3. Payment shall be made within 5 banking days<br/>
        <br/>
        <b>Signatures of the parties:</b><br/>
        _________________ [{from_org}]<br/>
        _________________ [{to_org}]<br/>
        """

        story.append(Paragraph(content, styles['Normal']))
        doc.build(story)
        return filename

    def import_organization_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите CSV файл", "",
                                                   "CSV Files (*.csv)")
        if not file_path: return

        org_names = self.get_organizations()
        if not org_names:
            QMessageBox.warning(self, "Ошибка", "Сначала добавьте организацию")
            return

        org_name, ok = QInputDialog.getItem(self, "Выбор организации", "Выберите организацию для импорта:",
                                            [org[1] for org in org_names], 0, False)
        if not ok: return

        org_id = next(org[0] for org in org_names if org[1] == org_name)

        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            required_columns = ['name', 'quantity', 'price']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                QMessageBox.warning(self, "Ошибка", f"В CSV отсутствуют колонки: {', '.join(missing_columns)}")
                return

            cursor = self.db.conn.cursor()
            imported_count = 0

            for _, row in df.iterrows():
                try:
                    cursor.execute(f'''
                        INSERT INTO products (org_id, name, quantity, price, category, sku)
                        VALUES ({org_id}, '{row['name']}', {int(row['quantity'])}, {float(row['price'])}, 
                                '{row.get('category', '')}', '{row.get('sku', '')}')
                    ''')
                    imported_count += 1
                except Exception as e:
                    print(f"Ошибка при импорте товара {row['name']}: {e}")

            self.db.conn.commit()
            QMessageBox.information(self, "Успех", f"Успешно импортировано {imported_count} товаров")
            self.load_all_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {str(e)}")

    def export_organizations(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "", "Excel Files (*.xlsx)")
        if not file_path: return

        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                'SELECT o.name, o.inn, o.address, o.phone, o.email, p.name, p.category, p.quantity, '
                'p.price FROM organizations o LEFT JOIN products p ON o.id = p.org_id')
            df = pd.DataFrame(cursor.fetchall(),
                              columns=['Организация', 'ИНН', 'Адрес', 'Телефон', 'Email', 'Товар', 'Категория',
                                       'Количество', 'Цена'])
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Успех", f"Данные экспортированы в {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {str(e)}")

    def generate_transactions_report(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет PDF", "",
                                                   "PDF Files (*.pdf)")
        if not file_path: return

        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT t.transaction_date, o1.name, o2.name, t.product_name, t.quantity, t.total_amount
                FROM transactions t
                JOIN organizations o1 ON t.from_org_id = o1.id
                JOIN organizations o2 ON t.to_org_id = o2.id
                ORDER BY t.transaction_date DESC LIMIT 20
            ''')

            data = [['Date', 'From', 'To', 'Product', 'Quantity', 'Amount']]
            for row in cursor.fetchall():
                data.append(
                    [row[0][:16], row[1], row[2], row[3], str(row[4]), f"{row[5]:,.0f} RUB" if row[5] else "0 RUB"])

            doc = SimpleDocTemplate(file_path, pagesize=A4)
            story = [Paragraph("Transactions Report", getSampleStyleSheet()['Title']),
                     Paragraph(f"Report generation date: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                               getSampleStyleSheet()['Normal']),
                     Paragraph("<br/>", getSampleStyleSheet()['Normal'])]

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(table)
            doc.build(story)
            QMessageBox.information(self, "Успех", f"Отчет сохранен: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка создания отчета: {str(e)}")

    def open_contract(self, index):
        row = index.row()
        contract_path = self.transactions_table.item(row, 7).text()
        if contract_path and os.path.exists(contract_path):
            os.startfile(contract_path)

    def get_organizations(self):
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name FROM organizations")
        return cursor.fetchall()


if __name__ == '__main__':
    sys.exit(pre_start())
