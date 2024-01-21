from flask import Flask,render_template,request,session
from flask_cors import CORS, cross_origin
import pymongo,certifi,json,time,copy,re

# auth parameter
app_secret_key = ""
MongoClient = ""

def create_app():
    app = Flask(__name__)
    cors = CORS(app, resources={r"/api/*": {"origins": "https://play.soulforged.net/"}})
    app.static_folder = 'static'
    app.secret_key=app_secret_key
    app.add_url_rule('/', 'resourceMap', resourceMap)
    app.add_url_rule('/dataSubmition', 'dataSubmit', dataSubmit, methods=["POST"])
    app.add_url_rule('/saveMapDot', 'saveMapDot', saveMapDot, methods=["POST"])
    app.add_url_rule('/delMapDot', 'delMapDot', delMapDot, methods=["POST"])
    app.add_url_rule('/addMapRoute', 'addMapRoute', addMapRoute, methods=["POST"])
    app.add_url_rule('/delMapRoute', 'delMapRoute', delMapRoute, methods=["POST"])
    app.add_url_rule('/getDataSet', 'getDataSet', getDataSet, methods=["POST"])
    app.add_url_rule('/JsonImput', 'dataImput', dataImput, methods=["POST"])
    app.add_url_rule('/checkVer', 'checkVer', checkVer)
    app.add_url_rule('/GetNodeList', 'GetNodeList', GetNodeList)
    app.add_url_rule('/GetNodeDict', 'GetNodeDict', GetNodeDict)
    app.add_url_rule('/SubmitNodeData', 'SubmitNodeData', SubmitNodeData, methods=["POST"])
    return app

dbName = 'resourceMap'
verNum = '1-4-3'
def pymongoConnection(databaseName, collectionName):
    ca=certifi.where()
    client = pymongo.MongoClient(MongoClient,tlsCAFile=ca)
    db = client[databaseName]
    collection=db[collectionName]
    return collection

def custom_sort(a, b):
    regex = re.compile(r"(\D+)(\d+)")  # 匹配開頭的字母和隨後的數字

    matchA = regex.match(a)
    matchB = regex.match(b)

    if matchA and matchB:
        prefixA, numberA = matchA.groups()
        prefixB, numberB = matchB.groups()

        numberA = int(numberA)
        numberB = int(numberB)

        # 先比較字母部分
        if prefixA < prefixB:
            return -1
        if prefixA > prefixB:
            return 1

        # 字母部分相同，比較數字部分
        return (numberA > numberB) - (numberA < numberB)

    # 如果不匹配，直接比較整個字符串
    return (a > b) - (a < b)

@cross_origin()
def GetNodeList():
    collection = pymongoConnection('resourceMapTest', 'idTable')
    dbData = collection.find_one({'dataType':'nodeId'},{'_id':0,'dataType':0})
    result = []
    for i in dbData:
        result.append(i)
    return str(result)

@cross_origin()
def GetNodeDict():
    collection = pymongoConnection('resourceMapTest', 'idTable')
    dbData = collection.find_one({'dataType':'nodeId'},{'_id':0,'dataType':0})
    return dbData

@cross_origin()
def SubmitNodeData():
    collection = pymongoConnection('resourceMapTest', 'idTable')
    dd = collection.find({},{'_id':0})
    idTable = {'node':{},'INV':{},'CRE':{}}
    newData = {}
    for i in dd:
        if i['dataType'] == 'nodeId':
            del i['dataType']
            idTable['node'] = i
        elif i['dataType'] == 'INV':
            del i['dataType']
            idTable['INV'] = i
        elif i['dataType'] == 'CRE':
            del i['dataType']
            idTable['CRE'] = i
        elif i['dataType'] == 'RES':
            del i['dataType']
            idTable['RES'] = i
    dataImput = request.json
    dataImput['node'] = str(dataImput['node'])
    # print(dataImput)
    newData['recordTime'] = int(time.time() * 1000)
    newData['recorder'] = dataImput['sender']
    if dataImput['node'] not in idTable['node']:
        return 'Node ID not yet paired.'
    newData['area'] = idTable['node'][dataImput['node']]
    if dataImput['dataType'] == 'Creatures' or dataImput['dataType'] == 'Resource':
        collection = pymongoConnection('resourceMapTest','hisStastic')
        his = collection.find_one({},{'_id':0,newData['area']:1})    
    errItemList = []
    errCreaturesList = []
    errResourceList = []
    if dataImput['dataType'] == 'Inventory':
        newData['item'] = []
        for item in dataImput['data']:
            oneItem = {}
            itemPath = dataImput['data'][item]['icon']
            itemId = itemPath[itemPath.rfind("/")+1:itemPath.find(".png")]
            oneItem['quentity'] = dataImput['data'][item]['amount']
            if itemId in idTable['INV']:
                oneItem['name'] = idTable['INV'][itemId]
                newData['item'].append(oneItem)
            else:
                errItemList.append({'dataType':'Inventory','id':itemId,'name':item})
        print(newData)
        collection = pymongoConnection('resourceMapTest','newestData')
        existCheck = collection.find_one({'area':newData['area']})
        if existCheck == None:
            newData['resource'] = []
            newData['animal'] = []
            collection.insert_one(newData)
        else:
            collection.update_one({'area':newData['area']},{'$set':newData})
        if len(errItemList) == 0:
            return 'OK'
        else:
            collection = pymongoConnection('resourceMapTest','unMapped')
            collection.insert_many(errItemList)
            return str(len(errItemList))+' creatures not yet paired.'
    elif dataImput['dataType'] == 'Creatures':
        newData['animal'] = []
        if newData['area'] not in his:
            newAnimalList = []
        elif 'animal' not in his[newData['area']]:
            newAnimalList = []
        else:
            newAnimalList = copy.deepcopy(his[newData['area']]['animal'])
        for creatures in dataImput['data']:
            if dataImput['data'][creatures]['hostile'] == False:
                continue
            aggCreatures = {}
            naggCreatures = {}
            creaturesId = creatures[creatures.rfind("/")+1:creatures.find(".png")]
            if creaturesId in idTable['CRE']:
                if dataImput['data'][creatures]['aggressive'] != 0:
                    aggCreatures['name'] = idTable['CRE'][creaturesId]
                    aggCreatures['activity'] = 1
                    aggCreatures['quentity'] = dataImput['data'][creatures]['aggressive']
                    newData['animal'].append(aggCreatures)
                if  dataImput['data'][creatures]['nonAggressive'] != 0:
                    naggCreatures['name'] = idTable['CRE'][creaturesId]
                    naggCreatures['activity'] = 0
                    naggCreatures['quentity'] = dataImput['data'][creatures]['nonAggressive']
                    newData['animal'].append(naggCreatures)
                if idTable['CRE'][creaturesId] not in newAnimalList:
                    newAnimalList.append(idTable['CRE'][creaturesId])
            else:
                errCreaturesList.append({'dataType':'Creatures','id':creaturesId})
        print(newData)
        collection = pymongoConnection('resourceMapTest','newestData')
        existCheck = collection.find_one({'area':newData['area']})
        if existCheck == None:
            newData['resource'] = []
            newData['item'] = []
            collection.insert_one(newData)
        else:
            collection.update_one({'area':newData['area']},{'$set':newData})
        if newData['area'] not in his:
            collection = pymongoConnection('resourceMapTest','hisStastic')
            collection.update_one({},{'$set':{newData['area']+'.animal':newAnimalList}})
        elif len(newAnimalList) != len(his[newData['area']]['animal']):
            collection = pymongoConnection('resourceMapTest','hisStastic')
            collection.update_one({},{'$set':{newData['area']+'.animal':newAnimalList}})
        if len(errCreaturesList) == 0:
            return 'OK'
        else:
            collection = pymongoConnection('resourceMapTest','unMapped')
            collection.insert_many(errCreaturesList)
            return str(len(errCreaturesList))+' creatures not yet paired.'
    elif dataImput['dataType'] == 'Resource':
        newData['resource'] = []
        if newData['area'] not in his:
            newResourceDict = {}
        elif 'resource' not in his[newData['area']]:
            newResourceDict = {}
        else:
            newResourceDict = copy.deepcopy(his[newData['area']]['resource'])
        hisChange = False
        for resource in dataImput['data']:
            oneResource = {}
            resourcePath = dataImput['data'][resource]['icon']
            resourceId = resourcePath[resourcePath.rfind("/")+1:resourcePath.find(".png")]
            oneResource['quentity'] = dataImput['data'][resource]['density']
            if resourceId in idTable['RES']:
                oneResource['name'] = idTable['INV'][resourceId]
                newData['resource'].append(oneResource)
                if oneResource['name'] not in newResourceDict:
                    newResourceDict[oneResource['name']] = {'max':oneResource['quentity'],'min':oneResource['quentity']}
                    hisChange = True
                else:
                    if oneResource['quentity'] > newResourceDict[oneResource['name']]['max']:
                        newResourceDict[oneResource['name']]['max'] = oneResource['quentity']
                        hisChange = True
                    if oneResource['quentity'] < newResourceDict[oneResource['name']]['min']:
                        newResourceDict[oneResource['name']]['max'] = oneResource['quentity']
                        hisChange = True
                print(newResourceDict)
            else:
                errResourceList.append({'dataType':'Resource','id':resourceId,'name':resource})
        print(newData)
        collection = pymongoConnection('resourceMapTest','newestData')
        existCheck = collection.find_one({'area':newData['area']})
        if existCheck == None:
            newData['item'] = []
            newData['animal'] = []
            collection.insert_one(newData)
        else:
            collection.update_one({'area':newData['area']},{'$set':newData})
        if hisChange:
            updateDict = {}
            for i in newResourceDict:
                updateDict[newData['area']+'.resource.'+oneResource['name']] = newResourceDict[oneResource['name']]
            collection = pymongoConnection('resourceMapTest','hisStastic')
            collection.update_one({},{'$set':updateDict})
        if len(errResourceList) == 0:
            return 'OK'
        else:
            collection = pymongoConnection('resourceMapTest','unMapped')
            collection.insert_many(errResourceList)
            return str(len(errResourceList))+' resource not yet paired.'
    elif dataImput['dataType'] == 'Location':
        print('spacing:',newData['area'],dataImput['data']['spacing'])
        collection = pymongoConnection('resourceMapTest','newestData')
        collection.update_one({'area':newData['area']},{'$set':{'space':dataImput['data']['spacing']}})
        collection = pymongoConnection('resourceMapTest','pathAP')
        querryOrList = []
        for i in dataImput['data']['paths']:
            querryOrList.append({'pathId':i})
        dd = collection.find({'$or':querryOrList},{'_id':0})
        if dd != None:
            for p in dd:
                if 'bAP' not in p and len(p['node']) != 2 and p['node'][0] != newData['area']:
                    data = {}
                    data['node'] = p['node']
                    data['node'].append(newData['area'])
                    data['bAP']= round((p['skillInfo'][0]['unitCost']*p['skillInfo'][0]['finalSpeed'])/6000,2)
                    collection.update_one({'pathId':p['pathId']},{'$set':data})

                    sorted_array = sorted(data['node'], key=lambda x: custom_sort(x, data['node'][0]))
                    collection = pymongoConnection('resourceMapTest','mapInfo')
                    dbNodeData = collection.find({},{'_id':0})
                    for i in dbNodeData:
                        if sorted_array[0] in i:
                            collection = pymongoConnection('resourceMapTest','mapRoute'+i['dataType'])
                            dbRouteData = collection.find_one({'start':sorted_array[0],'end':sorted_array[1]},{'_id':0})
                            if dbRouteData == None:
                                routeDict = {}
                                routeDict['start'] = sorted_array[0]
                                routeDict['end'] = sorted_array[1]
                                routeDict['color'] = '#ffffff'
                                routeDict['width'] = '2px'
                                routeDict['pathId'] = p['pathId']
                                routeDict['bAP'] = data['bAP']
                                collection.insert_one(routeDict)
                            else:
                                routeDict = {}
                                routeDict['pathId'] = p['pathId']
                                routeDict['bAP'] = data['bAP']
                                collection.update_one({'start':sorted_array[0],'end':sorted_array[1]},{'$set':routeDict})
                            break

        return 'OK'
    elif dataImput['dataType'] == 'TravelOperation':
        collection = pymongoConnection('resourceMapTest','pathAP')
        dd = collection.find_one({'pathId':dataImput['data']['pathId']},{'_id':0})
        if dd == None:
            data = {}
            data['pathId'] = dataImput['data']['pathId']
            data['node'] = [newData['area']]
            skillInfo = dataImput['data']['skillInfo']
            skillInfo['unitCost'] = dataImput['data']['unitCost']
            data['skillInfo'] = [skillInfo]
            collection.insert_one(data)
        elif 'bAP' not in dd and len(dd['node']) != 2 and dd['node'][0] != newData['area']:
                data = {}
                data['node'] = dd['node']
                data['node'].append(newData['area'])
                data['skillInfo'] = dd['skillInfo']
                skillInfo = dataImput['data']['skillInfo']
                skillInfo['unitCost'] = dataImput['data']['unitCost']
                data['skillInfo'].append(skillInfo)
                data['bAP']= round((data['skillInfo'][0]['unitCost']*data['skillInfo'][0]['finalSpeed'])/12000+(data['skillInfo'][1]['unitCost']*data['skillInfo'][1]['finalSpeed'])/12000,2)
                collection.update_one({'pathId':dataImput['data']['pathId']},{'$set':data})
                sorted_array = sorted(data['node'], key=lambda x: custom_sort(x, data['node'][0]))
                collection = pymongoConnection('resourceMapTest','mapInfo')
                dbNodeData = collection.find({},{'_id':0})
                for i in dbNodeData:
                    if sorted_array[0] in i:
                        collection = pymongoConnection('resourceMapTest','mapRoute'+i['dataType'])
                        dbRouteData = collection.find_one({'start':sorted_array[0],'end':sorted_array[1]},{'_id':0})
                        if dbRouteData == None:
                            routeDict = {}
                            routeDict['start'] = sorted_array[0]
                            routeDict['end'] = sorted_array[1]
                            routeDict['color'] = '#ffffff'
                            routeDict['width'] = '2px'
                            routeDict['pathId'] = dataImput['data']['pathId']
                            routeDict['bAP'] = data['bAP']
                            collection.insert_one(routeDict)
                        else:
                            routeDict = {}
                            routeDict['pathId'] = dataImput['data']['pathId']
                            routeDict['bAP'] = data['bAP']
                            collection.update_one({'start':sorted_array[0],'end':sorted_array[1]},{'$set':routeDict})
                        break
        print(newData)
        return 'OK'
    

def checkVer():
    return verNum
def getDataSet():
    item = request.form.get('item')
    if item =='newestData':
        collection = pymongoConnection(dbName, 'newestData')
        dbData = collection.find({},{'_id':0})
        data = {}
        for i in dbData:
            data[i['area']] = i
    elif item =='hisData':
        data = []
        collection = pymongoConnection(dbName, 'hisStastic')
        data = collection.find_one({},{'_id':0})
    elif item =='mapDotMain':
        collection = pymongoConnection(dbName, 'mapInfo')
        data = collection.find_one({'dataType':'Main'},{'_id':0,'dataType':0})
    elif item =='mapDotMH':
        collection = pymongoConnection(dbName, 'mapInfo')
        data = collection.find_one({'dataType':'MH'},{'_id':0,'dataType':0})
    elif item =='mapDotTT':
        collection = pymongoConnection(dbName, 'mapInfo')
        data = collection.find_one({'dataType':'TT'},{'_id':0,'dataType':0})
    elif item =='mapRouteMain':
        collection = pymongoConnection(dbName, 'mapRouteMain')
        dbData = collection.find({},{'_id':0})
        data = []
        for i in dbData:
            data.append(i)
    elif item =='mapRouteMH':
        collection = pymongoConnection(dbName, 'mapRouteMH')
        dbData = collection.find({},{'_id':0})
        data = []
        for i in dbData:
            data.append(i)
    elif item =='mapRouteTT':
        collection = pymongoConnection(dbName, 'mapRouteTT')
        dbData = collection.find({},{'_id':0})
        data = []
        for i in dbData:
            data.append(i)
    elif item =='nodeMaping':
        collection = pymongoConnection(dbName, 'idTable')
        data = collection.find_one({'dataType':'nodeId'},{'_id':0,'dataType':0})
    return str(data)
def resourceMap():
    result = {}
    if 'username' in session:
        result['username'] = session['username']
    collection = pymongoConnection(dbName, 'idTable')
    dbData = collection.find({},{'_id':0})
    for i in dbData:
        if i['dataType'] == 'nodeId':
            del i['dataType']
            result['nodeMaping'] = i
        elif  i['dataType'] == 'RES':
            del i['dataType']
            result['resMaping'] = i
        elif  i['dataType'] == 'CRE':
            del i['dataType']
            result['creMaping'] = i
        elif  i['dataType'] == 'INV':
            del i['dataType']
            result['invMaping'] = i
    return render_template('resourceMapV'+verNum+'.html',data = result)
def dataParse():
    result = {}
    if 'username' in session:
        result['username'] = session['username']
    collection = pymongoConnection(dbName, 'idTable')
    dbData = collection.find({},{'_id':0})
    
    for i in dbData:
        if i['dataType'] == 'nodeId':
            del i['dataType']
            result['jsonData'] = i
        elif  i['dataType'] == 'RES':
            del i['dataType']
            result['resMaping'] = i
        elif  i['dataType'] == 'CRE':
            del i['dataType']
            result['creMaping'] = i
        elif  i['dataType'] == 'INV':
            del i['dataType']
            result['invMaping'] = i
    collection = pymongoConnection(dbName, 'urlData')
    jsonData = collection.find_one({},{'_id':0})
    # with open('jsonData.json','r', encoding='utf-8') as f:
    #     jsonData = json.loads(f.read())
    result['nameData'] = jsonData
    return render_template('dataParseV1-0-4.html',data = result)
def dataSubmit():
    data = json.loads(request.form.get('data'))
    if "userName" in request.form:
        session['username'] = request.form.get('userName')
    data['recordTime'] = int(time.time() * 1000) 

    collection = pymongoConnection(dbName, 'hisStastic')
    ststicData = collection.find_one({},{'_id':0})
    if data['area'] in ststicData:
        for i in data['animal']:
            if i['name'] not in ststicData[data['area']]['animal']:
                ststicData[data['area']]['animal'].append(i['name'])
        for i in data['resource']:
            if i['name'] not in ststicData[data['area']]['resource']:
                ststicData[data['area']]['resource'][i['name']] = {'max':i['quentity'],'min':i['quentity']}
            else:
                if i['quentity'] > ststicData[data['area']]['resource'][i['name']]['max']:
                    ststicData[data['area']]['resource'][i['name']]['max'] = i['quentity']
                if i['quentity'] < ststicData[data['area']]['resource'][i['name']]['min']:
                    ststicData[data['area']]['resource'][i['name']]['min'] = i['quentity']
    else:
        ststicData = {}
        ststicData[data['area']] = {'animal':[],'resource':{'max':1,'min':4}}
        for i in data['animal']:
            if i['name'] not in ststicData[data['area']]['animal']:
                ststicData[data['area']]['animal'].append(i['name'])
        for i in data['resource']:
            if i['name'] not in ststicData[data['area']]['resource']:
                ststicData[data['area']]['resource'][i['name']] = {'max':i['quentity'],'min':i['quentity']}
            else:
                if i['quentity'] > ststicData[data['area']]['resource'][i['name']]['max']:
                    ststicData[data['area']]['resource'][i['name']]['max'] = i['quentity']
                if i['quentity'] < ststicData[data['area']]['resource'][i['name']]['min']:
                    ststicData[data['area']]['resource'][i['name']]['min'] = i['quentity']
    collection.update_one({},{'$set':{data['area']:ststicData[data['area']]}})


    collection = pymongoConnection(dbName, 'newestData')
    dbData = collection.find_one({'area':data['area']},{'_id':0})
    
    if dbData != None:
        collection.delete_one({'area':data['area']})
        if dbData['recordTime'] != 1697212800000:
            collection = pymongoConnection(dbName, 'hisData')
            dbData['abolishDate'] = data['recordTime']
            collection.insert_one(dbData)
    
    collection = pymongoConnection(dbName, 'newestData')
    collection.insert_one(data)
    return str(data['recordTime'])

def dataImput():
    dataType = request.form.get('type')
    data = json.loads(request.form.get('data'))
    print(dataType)
    print(data)
    if "userName" in request.form:
        session['username'] = request.form.get('userName')
    timeNow = int(time.time() * 1000) 
    # return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.localtime(time.time()+8*60*60))
    if dataType == 'nodeId':
        collection = pymongoConnection(dbName, 'idTable')
        dbData = collection.find_one({'dataType':'nodeId'},{'_id':0,'dataType':0})
        for oneData in data:
            keys_to_delete = [key for key, value in dbData.items() if value == oneData['mapNodeId']]
            unsetDict = {}
            for key in keys_to_delete:
                unsetDict[key] = 1
                del dbData[key]
            if oneData['authNodeId'] in dbData:
                if dbData[oneData['authNodeId']] != oneData['mapNodeId']:
                    collection = pymongoConnection(dbName, 'errorInput')
                    collection.insert_one({'datatype':'nodeId','data':data,'recordTime':timeNow})
                    return 'dataErr'
            else:
                dbData[oneData['authNodeId']] = oneData['mapNodeId']
        collection.update_one({'dataType':'nodeId'},{'$unset':unsetDict})
        collection.update_one({'dataType':'nodeId'},{'$set':dbData})
        return str(timeNow)
    elif dataType == 'RES':
        collection = pymongoConnection(dbName, 'idTable')
        collection.update_one({'dataType':'RES'},{'$set':data})
        return str(timeNow)
    elif dataType == 'CRE':
        collection = pymongoConnection(dbName, 'idTable')
        collection.update_one({'dataType':'CRE'},{'$set':data})
        return str(timeNow)
    elif dataType == 'INV':
        collection = pymongoConnection(dbName, 'idTable')
        collection.update_one({'dataType':'INV'},{'$set':data})
        return str(timeNow)
    elif dataType == 'Info':
        collection = pymongoConnection(dbName, 'dataCollect')
        data['recordTime'] = timeNow
        collection.insert_one(data)
        return str(timeNow)
    elif dataType == 'Issue':
        collection = pymongoConnection(dbName, 'errorInput')
        Issue = {'datatype':'mappingIssue','data':data,'recordTime':timeNow}
        if 'username' in session:
            Issue['recorder'] = session['username']
        collection.insert_one(Issue)
        return str(timeNow)
    elif dataType == 'Record':
        # print(data['area'])
        data['recordTime'] = timeNow
        collection = pymongoConnection(dbName, 'newestData')
        collection.update_one({'area':data['area']},{'$set':data})


        collection = pymongoConnection(dbName, 'hisStastic')
        ststicData = collection.find_one({},{'_id':0})
        if data['area'] in ststicData:
            for i in data['animal']:
                if i['name'] not in ststicData[data['area']]['animal']:
                    ststicData[data['area']]['animal'].append(i['name'])
            for i in data['resource']:
                if i['name'] not in ststicData[data['area']]['resource']:
                    ststicData[data['area']]['resource'][i['name']] = {'max':i['quentity'],'min':i['quentity']}
                else:
                    if i['quentity'] > ststicData[data['area']]['resource'][i['name']]['max']:
                        ststicData[data['area']]['resource'][i['name']]['max'] = i['quentity']
                    if i['quentity'] < ststicData[data['area']]['resource'][i['name']]['min']:
                        ststicData[data['area']]['resource'][i['name']]['min'] = i['quentity']
        else:
            ststicData = {}
            ststicData[data['area']] = {'animal':[],'resource':{'max':1,'min':4}}
            for i in data['animal']:
                if i['name'] not in ststicData[data['area']]['animal']:
                    ststicData[data['area']]['animal'].append(i['name'])
            for i in data['resource']:
                if i['name'] not in ststicData[data['area']]['resource']:
                    ststicData[data['area']]['resource'][i['name']] = {'max':i['quentity'],'min':i['quentity']}
                else:
                    if i['quentity'] > ststicData[data['area']]['resource'][i['name']]['max']:
                        ststicData[data['area']]['resource'][i['name']]['max'] = i['quentity']
                    if i['quentity'] < ststicData[data['area']]['resource'][i['name']]['min']:
                        ststicData[data['area']]['resource'][i['name']]['min'] = i['quentity']
        collection.update_one({},{'$set':{data['area']:ststicData[data['area']]}})


        collection = pymongoConnection(dbName, 'newestData')
        dbData = collection.find_one({'area':data['area']},{'_id':0})
        
        if dbData != None:
            collection.delete_one({'area':data['area']})
            if dbData['recordTime'] != 1697212800000:
                collection = pymongoConnection(dbName, 'hisData')
                dbData['abolishDate'] = timeNow
                collection.insert_one(dbData)
        
        collection = pymongoConnection(dbName, 'newestData')
        collection.insert_one(data)
        return str(timeNow)

def saveMapDot():
    collection = pymongoConnection(dbName, 'mapInfo')
    collection.update_one({'dataType':request.form.get('map')},{'$set':{request.form.get('id'):{'X':float(request.form.get('X')),'Y':float(request.form.get('Y'))}}})
    return 'OK'

def delMapDot():
    collection = pymongoConnection(dbName, 'mapRoute'+request.form.get('map'))
    collection.delete_many({'$or':[{'start':request.form.get('id')},{'end':request.form.get('id')}]})
    collection = pymongoConnection(dbName, 'idTable')
    dbData = collection.find_one({'dataType':'nodeId'},{'_id':0,'datatype':0})
    for i in dbData:
        if dbData[i] == request.form.get('id'):
            collection.update_one({'dataType':'nodeId'},{'$unset':{i:1}})
            break
    collection = pymongoConnection(dbName, 'mapInfo')
    collection.update_one({'dataType':request.form.get('map')},{'$unset':{request.form.get('id'):1}})
    return 'OK'

def addMapRoute():
    collection = pymongoConnection(dbName, 'mapRoute'+request.form.get('map'))
    jsonData = json.loads(request.form.get('data'))
    dbData = collection.find_one({'start':jsonData['start'],'end':jsonData['end']})
    if dbData == None:
        collection.insert_one(jsonData)
    else:
        collection.update_one({'start':jsonData['start'],'end':jsonData['end']},{'$set':{'color':jsonData['color'],'width':jsonData['width']}})
    return 'OK'
def delMapRoute():
    collection = pymongoConnection(dbName, 'mapRoute'+request.form.get('map'))
    collection.delete_one({'start':request.form.get('start'),'end':request.form.get('end')})
    return 'OK'
