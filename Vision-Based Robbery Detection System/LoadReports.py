import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
import firebase_admin
from firebase_admin import credentials, db


class ClickableLinkDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option.text = str(index.data())
        super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        if event.type() == event.MouseButtonRelease and event.button() == 1:
            url = index.data(Qt.UserRole)
            if url:
                QDesktopServices.openUrl(QUrl(url))
                return True
        return super().editorEvent(event, model, option, index)


class MainWindow(QMainWindow):


    def __init__(self):
        super().__init__()
        cred = credentials.Certificate("crime-detection-2be57-firebase-adminsdk-8g2rj-9c5d3b1b87.json")
        firebase_admin.initialize_app(cred, {
            "storageBucket": "crime-detection-2be57.appspot.com",
            "databaseURL": "https://crime-detection-2be57-default-rtdb.firebaseio.com"
        })
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Report')

        # Create a search bar with drop-down menu
        self.search_label = QLabel('Search by:')
        self.search_combobox = QComboBox()
        self.search_combobox.addItems(['Camera ID', 'City', 'State', 'Street', 'Incident Time'])
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Enter search term')
        self.search_button = QPushButton('Search')
        self.search_button.clicked.connect(self.search_table)

        # Create a table widget to display data
        self.table_widget = QTableWidget(self)
        self.table_widget.setColumnCount(9)
        self.table_widget.setHorizontalHeaderLabels(
            ['Camera ID', 'Additional Notes', 'City', 'State', 'Street', 'Bank Phone', 'Incident Description',
             'Incident Time', 'Image URL'])

        # Set size policy to make the table expandable
        self.table_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Populate the table with data from Firebase
        self.populate_table()

        # Set up the layout
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_combobox)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.table_widget)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Maximize the window
        self.setWindowState(Qt.WindowMaximized)

    def populate_table(self):
        incidents_ref = db.reference("incidents")
        incidents_snapshot = incidents_ref.get()

        if incidents_snapshot:
            for item in incidents_snapshot:
                for key, values in item.items():
                    rowPosition = self.table_widget.rowCount()
                    self.table_widget.insertRow(rowPosition)
                    self.table_widget.setItem(rowPosition, 0, QTableWidgetItem(str(values['camera_id'])))
                    self.table_widget.setItem(rowPosition, 1, QTableWidgetItem(values['additional_notes']))

                    address = values['address']
                    self.table_widget.setItem(rowPosition, 2, QTableWidgetItem(address.get('city', '')))
                    self.table_widget.setItem(rowPosition, 3, QTableWidgetItem(address.get('state', '')))
                    self.table_widget.setItem(rowPosition, 4, QTableWidgetItem(address.get('street', '')))

                    self.table_widget.setItem(rowPosition, 5, QTableWidgetItem(values['bank_phone']))
                    self.table_widget.setItem(rowPosition, 6, QTableWidgetItem(values['incident_description']))
                    self.table_widget.setItem(rowPosition, 7, QTableWidgetItem(values['incident_time']))
                    # Use setData to store the URL as a user role
                    url_item = QTableWidgetItem(values['image_url'])
                    url_item.setData(Qt.UserRole, values['image_url'])
                    self.table_widget.setItem(rowPosition, 8, url_item)
            # Set the custom delegate for the 'Image URL' column
            self.table_widget.setItemDelegateForColumn(8, ClickableLinkDelegate())
            # Set horizontal header stretch to make columns expand to the maximum width
            header = self.table_widget.horizontalHeader()
            for i in range(self.table_widget.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.Stretch)

            # Set the item stretches to make cells expand to the maximum size
            for row in range(self.table_widget.rowCount()):
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row, col)
                    if item is not None:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def search_table(self):
        search_term = self.search_edit.text().lower()
        search_column = self.search_combobox.currentText()
        column_index = self.get_column_index(search_column)

        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, column_index)
            if item.text().lower().find(search_term) != -1:
                self.table_widget.setRowHidden(row, False)
            else:
                self.table_widget.setRowHidden(row, True)

    def get_column_index(self, column_name):
        header_labels = self.table_widget.horizontalHeaderItem

        for i in range(self.table_widget.columnCount()):
            if header_labels(i).text() == column_name:
                return i


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
