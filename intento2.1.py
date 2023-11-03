from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QListWidget, QListWidgetItem, QSizePolicy, QHBoxLayout
from PyQt6.QtCore import QMetaObject, Qt, pyqtSignal, pyqtSlot, QSize, QTimer, QRect
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, NoiseTypes, FilterTypes
import sys
import numpy as np
from scipy import signal
import pyqtgraph as pg
import time
import sqlite3

class NeurobackApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NeuroBack - Patient Registration")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #1E3B4D; color: white;")

        self.patient_data = []

        self.init_ui()

    def init_ui(self):
        # Title label for NeuroBack
        self.label_title = QLabel("NeuroBack", self)
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = self.label_title.font()
        title_font.setPointSize(36)
        self.label_title.setFont(title_font)

        # Labels and input fields
        self.label_name = QLabel("Name:")
        self.entry_name = QLineEdit(self)

        self.label_age = QLabel("Age:")
        self.entry_age = QLineEdit(self)

        self.label_treatment = QLabel("Treatment Type:")
        self.entry_treatment = QLineEdit(self)

        self.label_sessions = QLabel("Number of Sessions:")
        self.entry_sessions = QLineEdit(self)

        # Button to save information
        self.btn_save = QPushButton("Save", self)
        self.btn_save.clicked.connect(self.save_data)

        # Button to view patient list
        self.btn_view_list = QPushButton("View Patient List", self)
        self.btn_view_list.clicked.connect(self.show_patient_list)

        # Layout of the main interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)

        # Center the title
        layout.addWidget(self.label_title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(self.label_name)
        layout.addWidget(self.entry_name)
        layout.addWidget(self.label_age)
        layout.addWidget(self.entry_age)
        layout.addWidget(self.label_treatment)
        layout.addWidget(self.entry_treatment)
        layout.addWidget(self.label_sessions)
        layout.addWidget(self.entry_sessions)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_view_list)

        # Set size policies for labels
        self.label_title.setSizePolicy(self.get_expanding_size_policy())
        self.label_name.setSizePolicy(self.get_expanding_size_policy())
        self.label_age.setSizePolicy(self.get_expanding_size_policy())
        self.label_treatment.setSizePolicy(self.get_expanding_size_policy())
        self.label_sessions.setSizePolicy(self.get_expanding_size_policy())

    def get_expanding_size_policy(self):
        size_policy = QSizePolicy()
        size_policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
        return size_policy

    def save_data(self):
        name = self.entry_name.text()
        age = self.entry_age.text()
        treatment = self.entry_treatment.text()
        sessions = self.entry_sessions.text()

        # Save data to database
        connection = sqlite3.connect("patient_data.db")
        cursor = connection.cursor()

        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id_patient INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                age INTEGER,
                treatment TEXT,
                sessions INTEGER
            )
        """)

        cursor.execute("INSERT INTO patients (name, age, treatment, sessions) VALUES (?, ?, ?, ?)",
            (name, age, treatment, sessions))
        # Commit changes
        connection.commit()

        # Close connection
        connection.close()

        # Clear the input fields
        self.entry_name.clear()
        self.entry_age.clear()
        self.entry_treatment.clear()
        self.entry_sessions.clear()


    def show_patient_list(self):
        # Display the list in a new window
        self.patient_list_window = PatientListWindow(self, self.patient_data)
        self.patient_list_window.setWindowTitle("Patient List")
        self.patient_list_window.setGeometry(100, 100, 600, 400)
        self.patient_list_window.setStyleSheet("background-color: #1E3B4D; color: white;")

        # Connect the patient selected signal to open session window
        self.patient_list_window.patientSelected.connect(self.open_session_window)
        # Connect the start session button signal
        self.patient_list_window.startSession.connect(self.open_session_window)
        # Connect the remove patient button signal
        self.patient_list_window.removePatient.connect(self.remove_patient)

        self.patient_list_window.show()

    @pyqtSlot(str)
    def open_session_window(self, selected_patient_name):
        # Open a new session window for the selected patient
        self.session_window = SessionWindow(selected_patient_name)
        self.session_window.show()

    @pyqtSlot(str)
    def remove_patient(self, patient_name):
        # Remove the patient from the patient list
        self.delete_patient_data(patient_name)

        # Update the patient list window
        self.patient_list_window.update_patient_list(self.patient_data)

    # New method to delete patient data
    def delete_patient_data(self, patient_name):
        self.patient_data = [patient for patient in self.patient_data if patient["Name"] != patient_name]


class PatientListWindow(QWidget):
    patientSelected = pyqtSignal(str)
    startSession = pyqtSignal(str)
    removePatient = pyqtSignal(str)

    def __init__(self, parent, patient_data):
        super().__init__()
        
        # Connect to the database
        connection = sqlite3.connect("patient_data.db")

        # Create a cursor
        cursor = connection.cursor()

        # Execute the query `SELECT * FROM patients`
        cursor.execute(f"SELECT * FROM patients")
        # Create a list to store the results
        patient_data = []
        row=[]
        # Iterate over the results of the query and add them to the list
        for row in cursor.fetchall():
            name=row[1]
            age=row[2]
            treatment=row[3]
            sessions=row[4]
            patient_data.append({"Name": name, "Age": age, "Treatment": treatment, "Sessions": sessions})
        
        print("La lista de pacientes es:" , patient_data)
        # Close the cursor and the connection to the database
        cursor.close()
        connection.close()
        self.parent = parent

        self.list_widget = QListWidget()

        for patient in patient_data:
            name = patient["Name"]
            age = patient["Age"]
            sessions = patient["Sessions"]

            item_text = f"Name: {name}, Age: {age}, Sessions: {sessions}"

            item = QListWidgetItem(item_text)
            item.setSizeHint(QSize(0, 80))

            btn_start_session = QPushButton("Start Session")
            btn_start_session.clicked.connect(lambda _, name=name: self.startSession.emit(name))

            btn_remove_patient = QPushButton("Remove Patient")
            btn_remove_patient.clicked.connect(lambda _, name=name: self.removePatient.emit(name))

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.addWidget(QLabel(item_text))  # Display the name
            layout.addWidget(btn_start_session)
            layout.addWidget(btn_remove_patient)

            container_item = QListWidgetItem()
            container_item.setSizeHint(QSize(0, 80))
            self.list_widget.addItem(container_item)
            self.list_widget.setItemWidget(container_item, widget)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)

    def update_patient_list(self, patient_data):
        self.list_widget.clear()

        for patient in patient_data:
            name = patient["Name"]
            age = patient["Age"]
            sessions = patient["Sessions"]

            item_text = f"Name: {name}, Age: {age}, Sessions: {sessions}"

            item = QListWidgetItem(item_text)
            item.setSizeHint(QSize(0, 80))

            btn_start_session = QPushButton("Start Session")
            btn_start_session.clicked.connect(lambda _, name=name: self.startSession.emit(name))

            btn_remove_patient = QPushButton("Remove Patient")
            btn_remove_patient.clicked.connect(lambda _, name=name: self.removePatient.emit(name))

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.addWidget(QLabel(item_text))  # Display the name
            layout.addWidget(btn_start_session)
            layout.addWidget(btn_remove_patient)

            container_item = QListWidgetItem()
            container_item.setSizeHint(QSize(0, 80))
            self.list_widget.addItem(container_item)
            self.list_widget.setItemWidget(container_item, widget)


class SessionWindow(QWidget):
    def __init__(self, patient_name):
        super().__init__()

        self.setWindowTitle(f"NeuroBack - Session Controls for {patient_name}")
        self.setGeometry(200, 200, 600, 400)
        self.setStyleSheet("background-color: #1E3B4D; color: white;")


        self.plot_duration = 5
        self.sample_frecuency=250
        self.plot_length=int(self.plot_duration*self.sample_frecuency)

        # Create a PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground((18,60,790))

        # Set the size of the PlotWidget
        #self.plot_widget.setFixedSize(800, 300)

        # Create a horizontal layout for the PlotWidget and buttons
        h_layout = QHBoxLayout()    
        h_layout.addWidget(self.plot_widget)

        # Create a vertical layout for the main window
        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(20, 20, 20, 20)

        # Add the horizontal layout to the vertical layout
        v_layout.addLayout(h_layout)

        # Add the buttons to the vertical layout
        btn_start_recording = QPushButton("Start Recording", self)
        btn_stop_session = QPushButton("Stop Session", self)
        btn_calc_PAF= QPushButton("Calculate PAF", self)
        btn_conectar=QPushButton("Connect Cyton", self)

        # Connect buttons to slots
        btn_start_recording.clicked.connect(self.start)
        btn_stop_session.clicked.connect(self.stop)
        btn_calc_PAF.clicked.connect(self.tomar_registro)
        btn_conectar.clicked.connect(self.connect_cyton)

        # Crear un layout horizontal para los botones
        h_button_layout = QHBoxLayout()
        h_button_layout.addWidget(btn_conectar)
        h_button_layout.addWidget(btn_start_recording)
        h_button_layout.addWidget(btn_stop_session)
        h_button_layout.addWidget(btn_calc_PAF)
        

        # Agregar el layout horizontal de botones al layout vertical principal
        v_layout.addLayout(h_button_layout)

        # Establecer el layout vertical principal en la ventana
        self.setLayout(v_layout)

        # # Add the vertical layout to the widget
        # self.setLayout(v_layout)

    @pyqtSlot()
    def connect_cyton(self):
        # SE ESTABLECE COMUNICACIÓN CON CYTHON
        # BoardShim.enable_board_logger()
        BoardShim.enable_dev_board_logger()
        params = BrainFlowInputParams()
        # params.serial_port = '/dev/ttyUSB0'
        params.serial_port = 'COM12'
        # params.timeout = 0
        # params.file = ''
        board_id = BoardIds.SYNTHETIC_BOARD.value
        #board_id = BoardIds.CYTON_BOARD.value
        self.board = BoardShim(board_id, params)
        self.board.prepare_session()

        # self.board.config_board('x1060100X')
        # self.board.config_board('x2160100X')
        # self.board.config_board('x3160100X')
        # self.board.config_board('x4160100X')
        # self.board.config_board('x5160100X')
        # self.board.config_board('x6160100X')
        # self.board.config_board('x7160100X')
        # self.board.config_board('x8160100X')

    def start(self):
        self.board.start_stream(900000)  # arranca la cyton
        print("START")
        time.sleep(2)

        self.x = [0]  
        self.y = [0]  
        pen = pg.mkPen(color=(106, 255, 164))
        self.data_line = self.plot_widget.plot(self.x, self.y, pen=pen)

        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def stop(self):
        self.board.stop_stream()
        data = self.board.get_board_data()
        DataFilter.write_file(data, 'Signal-EEG.csv', 'a')  # use 'a' for append mode
        print(len(data[0]))

        
        print("STOP")
        self.timer.stop()

    def update_plot_data(self):
        print("Updating plot data")
        newDATA = self.board.get_board_data()
        n = len(newDATA[0])  # Number of new data points

        # Extend 'x' and 'y' with the new data using NumPy
        new_x = np.arange(self.x[-1]+1, self.x[-1]+1 + n)
        new_y = newDATA[1]
        
        self.x = np.append(self.x, new_x)
        self.y = np.append(self.y, new_y)

        if len(self.y)>self.plot_length:
            y_plot=self.y[-self.plot_length:]
            x_plot=self.x[-self.plot_length:]*1/self.sample_frecuency
        else:
            y_plot=self.y
            x_plot=self.x*1/self.sample_frecuency
        print(self.y)
        self.data_line.setData(x_plot, y_plot)  # Update the data.
        DataFilter.write_file(newDATA,'Signal-EEG.csv', 'a')  # use 'a' for append mode
    
    def tomar_registro(self):
        # Cargamos los datos de las señales EEG desde un archivo
        lab= open("Signal-EEG.csv")
        datos = np.loadtxt(lab, delimiter="\t")
        datos=np.transpose(datos)
        datos=datos[1:] #Eliminamos la primer columna
        muestras=datos.shape[1]
        t = np.linspace(0,muestras/250, muestras)
        i=0
        eeg=np.zeros([3, muestras])
        for c in [5,6,7]:
            eeg[i]=datos[c]
            i+=1
        eog=np.zeros([2, muestras])
        i=0
        for c in [1,2]:
            eog[i]=datos[c]
            i+=1

        fs=250
        rest=eeg[0]
        
        # Filtra la señal en la banda de 8 a 12 Hz
        sos = signal.butter(2**5, [8, 12], 'band', analog=False, fs=250, output='sos')
        s_filt = signal.sosfiltfilt(sos, rest)
        # Calcula la frecuencia pico
        nper = int(fs * 0.75)
        f, DSP=signal.welch(s_filt, fs,  noverlap=nper//2, nperseg=nper)
        PAF=f[np.argmax(DSP)]
        
        # Imprime la frecuencia pico
        print(f"La frecuencia pico es {PAF} Hz")  

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NeurobackApp()
    window.show()
    sys.exit(app.exec())
