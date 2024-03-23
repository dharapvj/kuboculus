import sys
import datetime as dt
from humanize import naturaldelta
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QTableWidget, QMainWindow,
                               QTableWidgetItem, QListWidgetItem, QCheckBox)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from kubernetes import client, config

def nodeRole(labels: dict) -> str:
    roleLabel = next((label for label in labels.keys() if label.startswith("node-role.kubernetes.io/")),"")
    return roleLabel.removeprefix("node-role.kubernetes.io/")

def nodeTaintCount(taints: list) -> int:
    if not taints:
        return 0
    else:
        return len(taints)

def nodeStatus(conditions: list) -> str:
    cond: dict = next((cond for cond in conditions if cond.type == "Ready"), None)
    # print(f"{cond}")
    if cond and cond.status == 'True':
        return "Ready"
    return "NOTIMPL"   # TODO - figure out Nonready, Cordoned etc etc conditions!

def svcPorts(ports: list) -> str:
    ports=[f"{p.port}:{p.name}/{p.protocol}" for p in ports]
    # print(','.join(ports,))
    return ','.join(ports)

def svcExtIp(status: dict) -> str:
    if status.load_balancer and status.load_balancer.ingress:
        return status.load_balancer.ingress[0].ip
    return "-"

# TODO - see how we can respond back with some UI elements instead of strings
def svcSelectors(selectors: dict) -> str:
    # print(type(selectors))
    if selectors:
        sels=[f"{k}={v}" for k,v in selectors.items()]
        return ','.join(sels)
    return ""

def svcStatus(svcType: str, status: dict) -> str:
    if svcType == "LoadBalancer" and (not status.load_balancer.ingress or not status.load_balancer.ingress[0].ip) :
        return "Pending"
    return "Active"

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
    "Nodes": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Taints",
                "accessor": "nodeTaintCount(item.spec.taints)"
            }, {
                "name": "Roles",
                "accessor": "nodeRole(item.metadata.labels)"
            }, {
                "name": "Version",
                "accessor": "item.status.node_info.kubelet_version"
            }, {
                "name": "Conditions",
                "accessor": "nodeStatus(item.status.conditions)"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "ServiceAccounts": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Services": {
        "columns": [
            {
                "name": "Namespace",
                "accessor": "item.metadata.namespace"
            }, {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Type",
                "accessor": "item.spec.type"
            }, {
                "name": "Cluster IP",
                "accessor": "item.spec.cluster_ip"
            }, {
                "name": "Ports",
                "accessor": "svcPorts(item.spec.ports)"
            }, {
                "name": "External IP",
                "accessor": "svcExtIp(item.status)"
            }, {
                "name": "Selectors",
                "accessor": "svcSelectors(item.spec.selector)"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }, {
                "name": "Status",
                "accessor": "svcStatus(item.spec.type, item.status)"
            }],
        "data": []
    },
    "PersistentVolumes": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "PersistentVolumeClaims": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Events": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "ReplicaSets": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "StatefulSets": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "HorizontalPodAutoscalers": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Cronjobs": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Jobs": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "Ingresses": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
    "IngresseClasses": {
        "columns": [
            {
                "name": "Name",
                "accessor": "item.metadata.name"
            }, {
                "name": "Age",
                "accessor": "naturaldelta(dt.datetime.now(dt.timezone.utc) - item.metadata.creation_timestamp)"
            }],
        "data": []
    },
}

# Other Main API resource types to add:
# Add respective column definition for those resource types already added
# coreV1
#     endpoints
#     events
#     persistentvolumeclaims
#     persistentvolumes
#     nodes
#     serviceaccounts
#     services

# admissionregistration.k8s.io/v1
#     mutatingwebhookconfigurations
#     validatingwebhookconfigurations

# appsV1
#     replicasets
#     statefulsets

# autoscaling/v2
#     horizontalpodautoscalers

# batch/v1
#     cronjobs
#     jobs

# networking.k8s.io/v1
#     ingressclasses
#     ingresses
#     networkpolicies

# policy/v1
#     poddisruptionbudgets

# rbac.authorization.k8s.io/v1
#     clusterrolebindings
#     clusterroles
#     rolebindings
#     roles

# storage.k8s.io/v1
#     storageclasses
#     volumeattachments

# Relevant pod columns and their mapping
#Labels[]: .metadata.labels
#Annotations[]: .metadata.annotations
#Containers[]: .spec.containers
#InitContainers[]: .spec.init_containers
#Status??: .status.phase - Can also monitor the .status.conditions[]
# OR Status:  container_statuses[0].ready / started
namespaces = []

# TODO AGE calculation same as kubectl => https://github.com/kubernetes/apimachinery/blob/release-1.29/pkg/util/duration/duration.go#L48

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
        try:
            for colIndex, x in enumerate((resouceMapping[resourceType]).get('columns')):
                # print(f"{idx}, {colIndex}, {x}")
                table.setItem(idx, colIndex+1, QTableWidgetItem(str(eval(x['accessor']))))
        except KeyError:
            print(f"No proper data for accessor {x['accessor']} while evaluating value for col no {colIndex+1} for row {idx} for resourceType {resourceType}")
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
    autoscalingV2 = client.AutoscalingV2Api()
    batchV1 = client.BatchV1Api()
    networkingV1 = client.NetworkingV1Api()
    policyV1 = client.PolicyV1Api()
    rbacV1 = client.RbacAuthorizationV1Api()
    storageV1 = client.StorageV1Api()

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
        case "Nodes":
            ret = v1.list_node(watch=False)
        case "ServiceAccounts":
            ret = v1.list_service_account_for_all_namespaces(watch=False)
        case "Services":
            ret = v1.list_service_for_all_namespaces(watch=False)
        case "PersistentVolumes":
            ret = v1.list_persistent_volume(watch=False)
        case "PersistentVolumeClaims":
            ret = v1.list_persistent_volume_claim_for_all_namespaces(watch=False)
        case "Events":
            ret = v1.list_event_for_all_namespaces(watch=False)
        case "ReplicaSets":
            ret = appsV1.list_replica_set_for_all_namespaces(watch=False)
        case "StatefulSets":
            ret = appsV1.list_stateful_set_for_all_namespaces(watch=False)
        case "HorizontalPodAutoscalers":
            ret = autoscalingV2.list_horizontal_pod_autoscaler_for_all_namespaces(watch=False)
        case "Cronjobs":
            ret = batchV1.list_cron_job_for_all_namespaces(watch=False)
        case "Jobs":
            ret = batchV1.list_job_for_all_namespaces(watch=False)
        case "Ingresses":
            ret = networkingV1.list_ingress_for_all_namespaces(watch=False)
        case "IngressClasses":
            ret = networkingV1.list_ingress_class(watch=False)
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
    # TODO - allow choosing file using FileChooser
    config.load_kube_config(config_file='./kind.kubeconfig')

    loadNS()
    sys.exit(app.exec())

