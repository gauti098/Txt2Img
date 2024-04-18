from django.contrib.auth import get_user_model
from userlibrary.models import FileUpload
from campaign.models import (
    MainCampaign,GroupCampaign,
    GroupSingleCampaign,SoloCampaign
    )
from campaignAnalytics.models import (
    CampaignProspect,CampaignSingleAnalytics,
    CampaignGroupAnalytics
)
import json

userEmail = "demo@autogenerate.ai"
userInst = get_user_model().objects.get(email=userEmail)

campaignId = "089f6a44-0512-4e71-8e77-0e6c598f376d"
mainCampaign = MainCampaign.objects.get(id=campaignId)

salesPageJsonD = "{\"id\":395,\"name\":\"Salesforce <> Autogenerate.ai\",\"textEditor\":[{\"id\":1577,\"content\":\"<p class=\\\"ql-align-center\\\"   style=\\\" font-family: 'Poppins';\\n\\t\\t\\t\\tfont-size: 48px;\\n\\t\\t\\t\\tfont-weight: 900;\\n\\t\\t\\t\\tfont-stretch: normal;\\n\\t\\t\\t\\tfont-style: normal;\\n\\t\\t\\t\\tline-height: 1.46;\\n\\t\\t\\t\\tletter-spacing: 1.44px;\\n\\t\\t\\t\\ttext-align: center;\\n\\t\\t\\t\\tcolor: #e7416a;\\\">Salesforce &lt;&gt; AutoGenerate.ai</p>\",\"isDeleted\":false},{\"id\":1578,\"content\":\"<p class=\\\"ql-align-center\\\" style=\\\"font-family: Poppins; font-size: 1.25vw; font-weight: 900; font-stretch: normal; font-style: normal; line-height: 1.46; letter-spacing: 0.48px; text-align: center; color: rgb(255, 252, 242);\\\">Scalable Human Connection for David</p>\",\"isDeleted\":false},{\"id\":1579,\"content\":\"<p class=\\\"ql-align-center\\\" style=\\\"color: rgb(231, 65, 106);\\\"><strong style=\\\"font-size: 2.1875vw; color: rgb(231, 65, 106);\\\">Enter Your Text</strong></p>\",\"isDeleted\":true},{\"id\":1580,\"content\":\"<p class=\\\"ql-align-center\\\" style=\\\"color: rgb(34, 34, 34);\\\"><strong style=\\\"font-size: 1.25vw; color: rgb(34, 34, 34);\\\">johndoe@gmail.com | +1 187187 XXXX</strong></p>\",\"isDeleted\":true}],\"imageEditor\":[{\"id\":395,\"image\":\"https://api.autogenerate.ai/media/userlibrary/file/autogenerate.ai_logo_EgraJCH.svg\",\"height\":55,\"imgUrl\":\"https://autogenerate.ai\",\"isDeleted\":false}],\"buttonEditor\":[{\"id\":395,\"buttonData\":[{\"id\":2270,\"name\":\"Schedule Demo\",\"link\":\"http://autogenerate.ai/\",\"textColor\":\"#ffffffff\",\"buttonColor\":\"#e7416a\",\"isDeleted\":false,\"updated\":\"2021-07-11T13:19:46.454017Z\"},{\"id\":2271,\"name\":\"Button2\",\"link\":\"http://fb.com/\",\"textColor\":\"#FF0000\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-11T13:19:46.456559Z\"},{\"id\":2272,\"name\":\"Button3\",\"link\":\"http://fb.com/\",\"textColor\":\"#FF0000\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-11T13:19:46.459092Z\"},{\"id\":2273,\"name\":\"Button4\",\"link\":\"http://fb.com/\",\"textColor\":\"#FF0000\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-11T13:19:46.461541Z\"},{\"id\":2274,\"name\":\"button\",\"link\":\"\",\"textColor\":\"#e6e6e6\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-11T13:19:46.464116Z\"},{\"id\":2275,\"name\":\"button\",\"link\":\"\",\"textColor\":\"#e6e6e6\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-11T13:19:46.466421Z\"},{\"id\":2276,\"name\":\"button\",\"link\":\"\",\"textColor\":\"#e6e6e6\",\"buttonColor\":\"#e7416a\",\"isDeleted\":true,\"updated\":\"2021-07-11T13:19:46.468907Z\"}],\"isDeleted\":false}],\"iconEditor\":[{\"id\":1183,\"image\":\"https://api.autogenerate.ai/media/static/fbtemplate.svg\",\"link\":\"https://fb.com/\",\"isDeleted\":false},{\"id\":1184,\"image\":\"https://api.autogenerate.ai/media/static/linkedtemplate.svg\",\"link\":\"https://twitter.com/\",\"isDeleted\":false},{\"id\":1185,\"image\":\"https://api.autogenerate.ai/media/static/squaretemplate.svg\",\"link\":\"https://linkedin.com/\",\"isDeleted\":false}],\"videoEditor\":[{\"id\":395,\"height\":0,\"isDeleted\":false}],\"crouselEditor\":[{\"id\":395,\"crouselData\":[{\"id\":664,\"name\":\"Infographics\",\"media_type\":\"application/pdf\",\"media_file\":\"https://api.autogenerate.ai/media/userlibrary/file/collateral_infographic.pdf\",\"media_thumbnail\":\"https://api.autogenerate.ai/media/userlibrary/thumbnail/664_4f1fd8d5-d988-4dc5-8d37-034514f79e61.jpeg\",\"category\":\"upload\",\"timestamp\":\"2021-07-11T11:41:21.296946Z\",\"updated\":\"2021-07-11T11:45:19.290812Z\"},{\"id\":666,\"name\":\"Demo Video\",\"media_type\":\"video/mp4\",\"media_file\":\"https://api.autogenerate.ai/media/userlibrary/file/27c7e5cc-c2ef-11eb-bf88-fd9d708cc435_FfKQaRc_s0pt4Rb.mp4\",\"media_thumbnail\":\"https://api.autogenerate.ai/media/userlibrary/thumbnail/666_54de8288-e007-4049-9c59-f8f826acc1f3.jpeg\",\"category\":\"upload\",\"timestamp\":\"2021-07-11T11:42:49.079934Z\",\"updated\":\"2021-07-11T11:44:37.116394Z\",\"bgType\":4}],\"isDeleted\":false}],\"themeColorConfig\":{\"disabled\":false,\"colors\":{\"0\":\"#e7416a\",\"1\":\"#fffcf2\",\"2\":\"#222222\"}},\"publicId\":3,\"isPublish\":true,\"publicThemeColorCofig\":{\"disabled\":false,\"colors\":{\"0\":\"#e7416a\",\"1\":\"#fffcf2\",\"2\":\"#222222\"}}}"

COMMAND = (
    (0,'SENT'),
    (2,'OPENED'),
    (3,'VIDEO PLAYED'),
    (4,'CTA CLICKED'),
    (5,'CROUSEL CLICKED')
)
GCOMMAND = (
    (0,'SENT'),
    (1,'MAIL OPENED'),
    (2,'OPENED'),
    (3,'VIDEO PLAYED'),
    (4,'CTA CLICKED'),
    (5,'CROUSEL CLICKED')
)


#relative time in Seconds as int and str as static time
signalsData = [
    {"uniqueIdentity": "david@salesforce.com","type": "group","command": 4,"campaign": "Book Meetings","data": {"name": "Schedule Demo"}, "time": 0},
    {"uniqueIdentity": "david@salesforce.com","type": "group","command": 5,"campaign": "Book Meetings","data": {"name": "Demo Video"}, "time": 2*60},
    {"uniqueIdentity": "Oliver-Zoho on LinkedIn","type": "solo","command": 2,"campaign": "Book Meetings","data": {}, "time": 5*60},
    {"uniqueIdentity": "Oliver-Zoho on LinkedIn","type": "solo","command": 0,"campaign": "Book Meetings","data": {}, "time": 15*60},
    {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 3,"campaign": "New Subscription","data": {"name": "Explainer Video"}, "time": 7*60},
    {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 2,"campaign": "New Subscription","data": {}, "time": 9*60},
    {"uniqueIdentity": "david@salesforce.com","type": "group","command": 3,"campaign": "Book Meetings", "data": {"name": "Sales Pitch"},"time": 8 * 60},
    {"uniqueIdentity": "david@salesforce.com","type": "group","command": 2,"campaign": "Book Meetings", "data": {},"time": 9 * 60},
    {"uniqueIdentity": "david@salesforce.com","type": "group","command": 1,"campaign": "Book Meetings", "data": {},"time": 10 * 60},
    {"uniqueIdentity": "david@salesforce.com","type": "group","command": 0,"campaign": "Book Meetings", "data": {},"time": 15 * 60},
    {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 5,"campaign": "Trial Activation","data": {"name": "Infographics"}, "time": 12*60},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 4,"campaign": "Book Meetings","data": {"name": "Schedule Demo"}, "time": 17*60},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 5,"campaign": "Book Meetings","data": {"name": "Infographics"}, "time": 18*60},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 3,"campaign": "Book Meetings","data": {"name": "Sales Pitch"}, "time": 20*60},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 2,"campaign": "Book Meetings","data": {}, "time": 21*60},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 1,"campaign": "Book Meetings","data": {}, "time": 22*60},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 0,"campaign": "Book Meetings","data": {}, "time": 25*60},

    #prospect data
    {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 3,"campaign": "Trial Activation","data": {"name": "Explaner Video"}, "time": 12*60*60 + 58*60},
    {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 2,"campaign": "Trial Activation","data": {}, "time": 12*60*60 + 59*60},
    {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 1,"campaign": "Trial Activation","data": {}, "time": 13*60*60 + 3*60},
    {"uniqueIdentity": "oliver@hubspot.com","type": "group","command": 0,"campaign": "Trial Activation","data": {}, "time": 15*60*60 + 3*60},
    {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 1,"campaign": "New Subscription","data": {}, "time": "29-06-2021T19:39"},
    {"uniqueIdentity": "sophia@chorus.ai","type": "group","command": 0,"campaign": "New Subscription","data": {}, "time": "28-06-2021T19:38"},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 3,"campaign": "AutoGenerate Product...","data": {"name": "Sales Pitch"}, "time": "16-06-2021T17:09"},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 2,"campaign": "AutoGenerate Product...","data": {}, "time": "16-06-2021T17:08"},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 1,"campaign": "AutoGenerate Product...","data": {}, "time": "16-06-2021T17:04"},
    {"uniqueIdentity": "emma@dropbox.com","type": "group","command": 0,"campaign": "AutoGenerate Product...","data": {}, "time": "16-06-2021T13:04"},

]


salespageD = json.loads(salesPageJsonD)
mainCtaData = {}
for i in salespageD['buttonEditor']:
    if i['isDeleted'] == False:
        for j in i['buttonData']:
            if j['isDeleted'] == False:
                mainCtaData[j['id']] = {'name': j['name'],'isClicked': False}

mainCollateralData = {}
for i in salespageD['crouselEditor']:
    if i['isDeleted'] == False:
        for j in i['crouselData']:
            mainCollateralData[j['id']] = {'name': j['name'],'isClicked': False}



PSTATUS = (
    (0,'Pending'),
    (1,'Meeting Booked'),
    (2,'Snooze for 7 Days'),
    (3,'Snooze for 30 Days'),
    (4,'Sale Success'),
    (5,'Nothing Saled'),

)



prospectStatus = {"david@salesforce.com": 1,"sophia@chorus.ai": 4}

prospectOrder = []
prospectType = []
for ii in signalsData:
    uid = ii['uniqueIdentity']+'__'+ii['campaign']
    if uid not in prospectOrder:
        prospectOrder.append(uid)
        prospectType.append(ii['type'])
prospectType = prospectType[::-1]
prospectOrder = prospectOrder[::-1]
print(prospectOrder)




campaignCtaBtn = {}
campaignColBtn = {}
videoData = {}
for ii in signalsData:
    try:
        campaignCtaBtn[ii['campaign']]
    except:
        campaignCtaBtn[ii['campaign']] = []
    try:
        campaignColBtn[ii['campaign']]
    except:
        campaignColBtn[ii['campaign']] = []
    if ii['command'] == 3:
        videoData[ii['uniqueIdentity']+'__'+ii['campaign']]=  json.dumps({'name': ii['data']['name'],'isClicked': False})
    if ii['command'] == 4:
        campaignCtaBtn[ii['campaign']].append(ii['data']['name'])
    elif ii['command'] == 5:
        campaignColBtn[ii['campaign']].append(ii['data']['name'])

finalCtaPCamp = {}
campaignCtaData = {}
for ii in campaignCtaBtn:
    tdata = list(set(campaignCtaBtn[ii]))
    if len(tdata)==0:
        tdata = ['Book Meetings','Visit Website']
    mainD = {}
    if ii == mainCampaign.name:
        for jj in mainCtaData:
            data = mainCtaData[jj]
            try:
                campaignCtaData[ii][data['name']]= jj
            except:
                campaignCtaData[ii]={data['name']: jj}
        mainD = mainCtaData
    else:
        for n,jj in enumerate(tdata):
            mainD[n]= {'name': jj,'isClicked': False}
            try:
                campaignCtaData[ii][jj]=n
            except:
                campaignCtaData[ii]={jj: n}
    finalCtaPCamp[ii] = json.dumps(mainD)

finalColPCamp = {}
campaignColData = {}
for ii in campaignColBtn:
    tdata = list(set(campaignColBtn[ii]))
    if len(tdata)==0:
        tdata = ['Demo Video','Infographics']
    mainD = {}
    if ii == mainCampaign.name:
        for jj in mainCollateralData:
            data = mainCollateralData[jj]
            try:
                campaignColData[ii][data['name']]= jj
            except:
                campaignColData[ii]={data['name']: jj}
        mainD = mainCollateralData
    else:
        for n,jj in enumerate(tdata):
            mainD[n]= {'name': jj,'isClicked': False}
            try:
                campaignColData[ii][jj]=n
            except:
                campaignColData[ii]={jj: n}
    finalColPCamp[ii] = json.dumps(mainD)




createNewCampaign = []
allGroup = {}
allSolo = {}
for anaylData in signalsData:
    if anaylData['campaign'] not in createNewCampaign:
        createNewCampaign.append(anaylData['campaign'])
        if anaylData['type'] == 'group':
            allGroup[anaylData['campaign']] = [anaylData['uniqueIdentity']]
            allSolo[anaylData['campaign']] = []
        else:
            allSolo[anaylData['campaign']] = [anaylData['uniqueIdentity']]
            allGroup[anaylData['campaign']] =[]
    else:
        if anaylData['type'] == 'group':
            if anaylData['uniqueIdentity'] not in allGroup[anaylData['campaign']]:
                allGroup[anaylData['campaign']].append(anaylData['uniqueIdentity'])
        else:
            if anaylData['uniqueIdentity'] not in allSolo[anaylData['campaign']]:
                allSolo[anaylData['campaign']].append(anaylData['uniqueIdentity'])

        

campaignInst = {}
for campName in createNewCampaign:
    try:
        inst = MainCampaign.objects.get(user=userInst,name=campName)
        campaignInst[campName] = inst
    except:
        inst = MainCampaign(user=userInst,name=campName,video=mainCampaign.video,salespage=mainCampaign.salespage)
        inst.save()
        campaignInst[campName] = inst



groupDataInst = {}
## create group campaign
for singleCamp in allGroup:
    campData = allGroup[singleCamp]
    try:
        inst = GroupCampaign.objects.get(campaign=campaignInst[singleCamp])
        inst.isValidated = False
        inst.mergeTagMap=json.dumps({"{{GroupEmailId}}": "email"})
        inst.save()
    except:
        inst = GroupCampaign(campaign=campaignInst[singleCamp],mergeTagMap=json.dumps({"{{GroupEmailId}}": "email"}),isAdded=True,isValidated=False,totalData=len(campData),isGenerated=True,csvFile=FileUpload.objects.all().first())
        inst.save()
    for unQi in campData:
        try:
            sgroupInst = GroupSingleCampaign.objects.get(groupcampaign=inst,uniqueIdentity=unQi)
            sgroupInst.data=json.dumps({"{{GroupEmailId}}": unQi})
            sgroupInst.salesPageData=salesPageJsonD
            sgroupInst.save()
        except:
            sgroupInst = GroupSingleCampaign(groupcampaign=inst,uniqueIdentity=unQi,data=json.dumps({"{{GroupEmailId}}": unQi}),genVideo=campaignInst[singleCamp].video.generateStatus,salesPageData=salesPageJsonD)
            sgroupInst.save()
        groupDataInst[unQi+'__'+singleCamp] = sgroupInst


soloDataInst = {}
for singleCamp in allSolo:
    campData = allSolo[singleCamp]
    for unQi in campData:
        try:
            sgroupInst = SoloCampaign.objects.get(uniqueIdentity=unQi,campaign=campaignInst[singleCamp])
            sgroupInst.salesPageData=salesPageJsonD
            sgroupInst.save()
        except:
            sgroupInst = SoloCampaign(uniqueIdentity=unQi,campaign=campaignInst[singleCamp],data=json.dumps({"{{GroupEmailId}}": unQi}),genVideo=campaignInst[singleCamp].video.generateStatus,salesPageData=salesPageJsonD)
            sgroupInst.save()
        soloDataInst[unQi+'__'+singleCamp] = sgroupInst

## create Prospect
mainProspect = {}
for nn,uniqueIdentity in enumerate(prospectOrder):
    if prospectType[nn] == 'group':
        groupInstC = groupDataInst[uniqueIdentity]
        uniqueIdentity = uniqueIdentity.split('__')[0]
        crntInst = CampaignProspect.objects.filter(campaign=groupInstC.groupcampaign.campaign,uniqueIdentity=uniqueIdentity,groupm=groupInstC)
        for ii in crntInst:
            ii.delete()

        crntInst = CampaignProspect(campaign=groupInstC.groupcampaign.campaign,uniqueIdentity=uniqueIdentity,groupm=groupInstC)
        crntInst.save()
        
        crntInst.ctaData = finalCtaPCamp[groupInstC.groupcampaign.campaign.name]
        try:
            crntInst.videoData = videoData[uniqueIdentity]
        except:
            pass
        crntInst.collateralData = finalColPCamp[groupInstC.groupcampaign.campaign.name]
        crntInst.save()
        mainProspect[uniqueIdentity+'__'+crntInst.campaign.name]=crntInst
    else:
        groupInstC = soloDataInst[uniqueIdentity]
        uniqueIdentity = uniqueIdentity.split('__')[0]

        crntInst = CampaignProspect.objects.filter(campaign=groupInstC.campaign,uniqueIdentity=uniqueIdentity,solom=groupInstC)
        for ii in crntInst:
            ii.delete()

        crntInst = CampaignProspect(campaign=groupInstC.campaign,uniqueIdentity=uniqueIdentity,solom=groupInstC)
        crntInst.save()
        crntInst.ctaData = finalCtaPCamp[groupInstC.campaign.name]
        crntInst.collateralData = finalColPCamp[groupInstC.campaign.name]
        try:
            crntInst.videoData = videoData[uniqueIdentity]
        except:
            pass
        crntInst.save()
        mainProspect[uniqueIdentity+'__'+crntInst.campaign.name]=crntInst

print(mainProspect)
# for uniqueIdentity in groupDataInst:
#     groupInstC = groupDataInst[uniqueIdentity]
#     uniqueIdentity = uniqueIdentity.split('__')[0]

    
#     crntInst = CampaignProspect.objects.filter(campaign=groupInstC.groupcampaign.campaign,uniqueIdentity=uniqueIdentity,groupm=groupInstC)
#     for ii in crntInst:
#         ii.delete()

#     crntInst = CampaignProspect(campaign=groupInstC.groupcampaign.campaign,uniqueIdentity=uniqueIdentity,groupm=groupInstC)
#     crntInst.save()
#     crntInst.ctaData = finalCtaPCamp[groupInstC.groupcampaign.campaign.name]
#     crntInst.collateralData = finalColPCamp[groupInstC.groupcampaign.campaign.name]
#     crntInst.save()
#     mainProspect[uniqueIdentity+'__'+crntInst.campaign.name]=crntInst

# for uniqueIdentity in soloDataInst:
#     groupInstC = soloDataInst[uniqueIdentity]
#     uniqueIdentity = uniqueIdentity.split('__')[0]

#     crntInst = CampaignProspect.objects.filter(campaign=groupInstC.campaign,uniqueIdentity=uniqueIdentity,solom=groupInstC)
#     for ii in crntInst:
#         ii.delete()

#     crntInst = CampaignProspect(campaign=groupInstC.campaign,uniqueIdentity=uniqueIdentity,solom=groupInstC)
#     crntInst.save()
#     crntInst.ctaData = finalCtaPCamp[groupInstC.campaign.name]
#     crntInst.collateralData = finalColPCamp[groupInstC.campaign.name]
#     crntInst.save()
#     mainProspect[uniqueIdentity+'__'+crntInst.campaign.name]=crntInst

from datetime import datetime,timedelta
from django.utils import timezone

updatedTime = {}
## add data to signals
for ii in signalsData:
    #relative time
    if type(ii['time'])==int:
        now = timezone.now()
        timeDateTime = now - timedelta(0,ii['time'])
    else:
        timeDateTime = datetime.strptime(ii['time'], '%d-%m-%YT%H:%M').replace(tzinfo=timezone.utc)

    if ii['type'] != 'group':
        if ii['command'] == 0:
            try:
                inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
            except:
                allQ = CampaignSingleAnalytics.objects.filter(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
                allQ.delete()
                inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
        elif ii['command'] == 2:
            try:
                inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
            except:
                allQ = CampaignSingleAnalytics.objects.filter(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
                allQ.delete()
                inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
        elif ii['command'] == 3:
            inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=3,data=str(0),cData=json.dumps({'name': ii['data']['name']}))
        elif ii['command'] == 4:
            btnName = ii['data']['name']
            vdata = campaignCtaData[ii['campaign']][btnName]
            cData = {'id': vdata,'name': btnName}
            inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=4,data=str(vdata),cData=json.dumps(cData))
        elif ii['command'] == 5:
            btnName = ii['data']['name']
            vdata = campaignColData[ii['campaign']][btnName]
            cData = {'id': vdata,'name': btnName}
            inst_,ct = CampaignSingleAnalytics.objects.get_or_create(campaign=soloDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=5,data=str(vdata),cData=json.dumps(cData))
        inst_.timestamp=timeDateTime
        inst_.save()

    else:
        if ii['command'] == 0:
            inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=0)
        elif ii['command'] == 1:
            inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=1)
        elif ii['command'] == 2:
            inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=2)
        elif ii['command'] == 3:
            inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=3,data=str(0),cData=json.dumps({'name': ii['data']['name']}))
        elif ii['command'] == 4:
            btnName = ii['data']['name']
            vdata = campaignCtaData[ii['campaign']][btnName]
            cData = {'id': vdata,'name': btnName}
            inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=4,data=str(vdata),cData=json.dumps(cData))
        elif ii['command'] == 5:
            btnName = ii['data']['name']
            vdata = campaignColData[ii['campaign']][btnName]
            cData = {'id': vdata,'name': btnName}
            inst_,ct = CampaignGroupAnalytics.objects.get_or_create(campaign=groupDataInst[ii['uniqueIdentity']+'__'+ii['campaign']],command=5,data=str(vdata),cData=json.dumps(cData))
        inst_.timestamp=timeDateTime
        inst_.save()

    try:
        getPrvTime = updatedTime[ii['uniqueIdentity']+'__'+ii['campaign']]
        if getPrvTime<timeDateTime:
            updatedTime[ii['uniqueIdentity']+'__'+ii['campaign']] = timeDateTime
    except:
        updatedTime[ii['uniqueIdentity']+'__'+ii['campaign']] = timeDateTime
        #curntProspect = mainProspect[ii['uniqueIdentity']+'__'+ii['campaign']]
        # if curntProspect.timestamp>timeDateTime:
        #     curntProspect.timestamp = timeDateTime
        #     curntProspect.save()

for ii in updatedTime:
    tmp = mainProspect[ii]
    print(tmp.id,updatedTime[ii])
    t = CampaignProspect.objects.filter(id=tmp.id)
    t.update(updated=updatedTime[ii])


for ii in prospectStatus:
    tmp = CampaignProspect.objects.filter(uniqueIdentity=ii)
    tmp.update(prospectStatus=prospectStatus[ii])