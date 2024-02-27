import sys
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QTableWidget,
                               QTableWidgetItem)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from kubernetes import client, config

#TODO: the global variable means we can only have one call at a time?
pods =[]

def populateTable(index):
    currNamespace = window.comboBox.currentText()
    print(f"selected index is {index}, {currNamespace}")

    table = window.tableWidget
    table.setColumnCount(3) # FIXME: right now hardcoded at 3
    table.setColumnWidth(1, 340)
    table.setHorizontalHeaderLabels(["Namespace", "Name", "IP"])
    table.clear()
    print(f"about to enumerate {len(pods)}")
#    # TODO: QTableView is probably better for structured data but needs to define model.

    # TODO: filter the pods then use filtered collection instead also to set row count
    table.setRowCount(len(pods))
    for idx, item in enumerate(pods):
        print("enumerating")
        print(f"{currNamespace}, {item.metadata.namespace}")
        if currNamespace == "ALL" or currNamespace == item.metadata.namespace:
            print("adding data in row")
            namespace = QTableWidgetItem(item.metadata.namespace)
            name = QTableWidgetItem(item.metadata.name)
            ip = QTableWidgetItem(item.status.pod_ip)
            table.setItem(idx, 0, namespace)
            table.setItem(idx, 1, name)
            table.setItem(idx, 2, ip)
    table.setSortingEnabled(True)
    
def loadTable(table):
    global pods
    config.load_kube_config(config_file='./kind.kubeconfig')
    
    v1 = client.CoreV1Api()
    print("Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    pods = ret.items
    print("Got list")
    populateTable(-1)



if __name__ == "__main__":
    ui_file_name = "trial-screen.ui"
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QFile.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)
    print("Loading the ui file into runtime")
    loader = QUiLoader()
    # Note: Appl must be created AFTER QUiLoader
    app = QApplication(sys.argv)
    window = loader.load(ui_file, None)
    print("Loading the ui file into runtime completed")
    ui_file.close()
    if not window:
        print(loader.errorString())
        sys.exit(-1)
    window.show()
    window.comboBox.addItems(["ALL","default", "kube-system"])
    window.comboBox.currentIndexChanged.connect(populateTable)
    loadTable(window.tableWidget)
    sys.exit(app.exec())


#   sys.exit(app.exec())
#   