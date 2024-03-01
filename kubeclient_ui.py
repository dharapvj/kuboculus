import sys
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QTableWidget,
                               QTableWidgetItem, QListWidgetItem)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from kubernetes import client, config

#TODO: the global variable means we can only have one call at a time?
# pods =[]
# deployments = []

# We should have a tuple .. Name of column and mapped attribute so that whole process can become dynamic
resouceMapping = {
    "Pods": {
        "columns": ["Namespace", "Name", "IP"],
        "data": []
    },
    "Deployments": {
        "columns": ["Namespace", "Name", "replicas"],
        "data": []
    }
}

# Relevant pod columns and their mapping
#Labels[]: .metadata.labels
#Annotations[]: .metadata.annotations
#Containers[]: .spec.containers
#InitContainers[]: .spec.init_containers
#Status??: .status.phase - Can also monitor the .status.conditions[]
# OR Status:  container_statuses[0].ready / started
namespaces = []


def repopulateTable(resourceType):
    print(f"list selection changed to {resourceType}")
    loadTable(window.resourceTable, resourceType)

def populateTable(index):
    currNamespace = window.namespaces.currentText()

    table = window.resourceTable
    resourceType = window.resourceTypeList.currentItem().text()
    print(f"whats hot: {resourceType}, {index}")
    cols = resouceMapping[resourceType]['columns']
    table.setColumnCount(len(cols))
    table.setColumnWidth(1, 340)
    table.setRowCount(0)
    table.setHorizontalHeaderLabels(cols)
    # print(f"about to enumerate {deployments[0]}")
    # TODO: QTableView is probably better for structured data but needs to define model.

    if currNamespace != "ALL":
        filterdList = [o for o in resouceMapping[resourceType]['data'] if currNamespace == o.metadata.namespace]
    else:
        filterdList = resouceMapping[resourceType]['data']
    table.setRowCount(len(filterdList))

    for idx, item in enumerate(filterdList):
        match resourceType:
            case "Pods":
                namespace = QTableWidgetItem(item.metadata.namespace)
                name = QTableWidgetItem(item.metadata.name)
                ip = QTableWidgetItem(item.status.pod_ip)
                table.setItem(idx, 0, namespace)
                table.setItem(idx, 1, name)
                table.setItem(idx, 2, ip)
            case "Deployments":
                namespace = QTableWidgetItem(item.metadata.namespace)
                name = QTableWidgetItem(item.metadata.name)
                replicas = QTableWidgetItem(str(item.status.ready_replicas)+"/"+str(item.status.replicas))
                table.setItem(idx, 0, namespace)
                table.setItem(idx, 1, name)
                table.setItem(idx, 2, replicas)
    table.setSortingEnabled(True)

def loadNS():
    global namespaces
    window.namespaces.addItems(["ALL"])
    v1 = client.CoreV1Api()
    ret = v1.list_namespace(watch=False)
    namespaces = ret.items
    nsIter = map(lambda ns: ns.metadata.name, namespaces)
    window.namespaces.addItems(nsIter)
    window.namespaces.currentIndexChanged.connect(populateTable)


def loadTable(table, resourceType):
    global resouceMapping
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    v1 = client.CoreV1Api()
    appsV1 = client.AppsV1Api()

    match resourceType:
        case "Pods":
            ret = v1.list_pod_for_all_namespaces(watch=False)
        case "Deployments":
            ret = appsV1.list_deployment_for_all_namespaces(watch=False)
        # case "configmaps":
        #     print("configmaps")
        case _:
            print("Resouce Type NOT IMPLEMETED")
    resouceMapping[resourceType]['data'] = ret.items
    populateTable(-1);

def populateResourceTypeList():
    resouceTypeWidget = window.resourceTypeList
    QListWidgetItem("Pods", resouceTypeWidget);
    QListWidgetItem("Deployments", resouceTypeWidget);
    # QListWidgetItem("ConfigMaps", resouceTypeWidget);

    # in the end - connect to a change event
    window.resourceTypeList.currentTextChanged.connect(repopulateTable)


if __name__ == "__main__":
    ui_file_name = "trial-screen.ui"
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QFile.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)
    print("Loading the ui file into runtime")
    loader = QUiLoader()
    # Note: Application must be created AFTER QUiLoader
    app = QApplication(sys.argv)
    window = loader.load(ui_file, None)
    print("Loading the ui file into runtime completed")
    ui_file.close()
    if not window:
        print(loader.errorString())
        sys.exit(-1)

    populateResourceTypeList()
    window.show()

    # kube api access
    config.load_kube_config(config_file='./kind.kubeconfig')

    loadNS()
    sys.exit(app.exec())

