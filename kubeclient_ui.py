import sys
import datetime as dt
from humanize import naturaldelta
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QTableWidget, QMainWindow,
                               QTableWidgetItem, QListWidgetItem, QCheckBox)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from kubernetes import client, config

#TODO: the global variable means we can only have one call at a time?
# We should have a tuple .. Name of column and mapped attribute so that whole process can become dynamic
resouceMapping = {
    "Pods": {
        "columns": [
            {
                "name": "Namespace",
                "accessor": "item.metadata.namespace"
            }, {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Node",
                "accessor": "item.spec.node_name"
            }, {
                "name": "IP",
                "accessor": "item.status.pod_ip"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Deployments": {
        "columns": [
            {
                "name": "Namespace",
                "accessor": "item.metadata.namespace"
            }, {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Replicas",
                "accessor": "str(item.status.ready_replicas)+\"/\"+str(item.status.replicas)"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "ConfigMaps": {
        "columns": [
            {
                "name": "Namespace",
                "accessor": "item.metadata.namespace"
            }, {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Keys",
                "accessor": "len(item.data)"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Secrets": {
        "columns": [
            {
                "name": "Namespace",
                "accessor": "item.metadata.namespace"
            }, {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Keys",
                "accessor": "len(item.data)"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Daemonsets": {
        "columns": [
            {
                "name": "Namespace",
                "accessor": "item.metadata.namespace"
            }, {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Node Selector",
                "accessor": "item.spec.template.spec.node_selector"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
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

# AGE calculation = https://github.com/kubernetes/apimachinery/blob/release-1.29/pkg/util/duration/duration.go#L48

def repopulateTable(resourceType):
    print(f"list selection changed to {resourceType}")
    loadTable(window.resourceTable, resourceType)

def populateTable(index):
    currNamespace: str = window.namespaces.currentText()

    table: QTableWidget = window.resourceTable
    resourceType = window.resourceTypeList.currentItem().text()
    # print(f"Page: {resourceType}, NS Index: {index}")
    # print(f"Page: { (resouceMapping[resourceType]).get('columns')}")
    colNames = [ col['name'] for col in (resouceMapping[resourceType]).get('columns')] 
    table.setColumnCount(1+len(colNames)) # one column for checkbox
    colNames.insert(0, "Select") # TODO - can we convert this into a checkbox as well? https://forum.qt.io/topic/15084/solved-pyside-1-1-0-putting-a-checkbox-in-horizontalheader-of-qtablewidget/3
    # TODO: default column width also move to mapping
    table.setColumnWidth(2, 340)
    table.setRowCount(0)
    table.setHorizontalHeaderLabels(colNames)

    # TODO: QTableView is probably better for structured data but needs to define model.

    if currNamespace != "ALL":
        filterdList = [o for o in resouceMapping[resourceType]['data'] if currNamespace == o.metadata.namespace]
    else:
        filterdList = resouceMapping[resourceType]['data']
    table.setRowCount(len(filterdList))

    # if resourceType == "Daemonsets":
    #     print(f"about to enumerate {filterdList[0]}")

    for idx, item in enumerate(filterdList):
        # print(f"item ns? {eval('item.metadata.namespace')}" )
        # Add checkbox column
        # TODO: how to center it https://falsinsoft.blogspot.com/2013/11/qtablewidget-center-checkbox-inside-cell.html
        chkBoxItem = QCheckBox()
        # chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        # chkBoxItem.setCheckState(QtCore.Qt.Unchecked)       
        table.setCellWidget(idx,0,chkBoxItem)
        # add data columns
        for colIndex, x in enumerate((resouceMapping[resourceType]).get('columns')):
            # print(f"{idx}, {colIndex}, {x}")
            table.setItem(idx, colIndex+1, QTableWidgetItem(str(eval(x['accessor']))))
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
        case "ConfigMaps":
            ret = v1.list_config_map_for_all_namespaces(watch=False)
        case "Secrets":
            ret = v1.list_secret_for_all_namespaces(watch=False)
        case "Daemonsets":
            ret = appsV1.list_daemon_set_for_all_namespaces(watch=False)
        case _:
            print("Resouce Type NOT IMPLEMETED")
    resouceMapping[resourceType]['data'] = ret.items
    populateTable(-1);

def populateResourceTypeList():
    resouceTypeWidget = window.resourceTypeList

    for res in resouceMapping:
        print(res)
        QListWidgetItem(res, resouceTypeWidget);

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
    window: QMainWindow = loader.load(ui_file, None)
    avGeom = app.primaryScreen().geometry()
    # print(f"{avGeom}")
    window.setGeometry(avGeom)
    window.setWindowTitle("Kuboculus - Control all your Kubernetes clusters from one app!")
    
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

