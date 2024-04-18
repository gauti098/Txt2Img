def generateAiVideo(DEVICE=settings.DEVICE):
    time.sleep(10)
    melstepsize = settings.WAVLIPMELSTEPSIZE
    allAvatarImgSeq = {}
    try:
        resQuery = GeneratedFinalVideo.objects.filter(Q(status=0) | Q(status=4))
        for qq in resQuery:
            qq.status = 2
            qq.save()
        while True:
            try:
                query = GeneratedFinalVideo.objects.filter(status=2).order_by('isDefault','-priority')
            except:
                time.sleep(10)
                continue
            
            try:
                firstQueueData = query.first()
                isErrorFlag = False
                if firstQueueData:
                    firstQueueData.setupTotalFrames()
                    currentProcessingFrame = 0
                    

                    firstQueueData.status = 4
                    firstQueueData.save()
                    print('Found New Task ',firstQueueData.id)
                    allThread = []
                    totalScene = firstQueueData.multipleScene.singleScene.all()
                    totalSceneCount = totalScene.count() - 1
                    
                    uniqueData = json.loads(firstQueueData.output)
                    allScenes = uniqueData['scenes']
                    
                    for crntSc,singleScene in enumerate(totalScene):
                        print('Starting: ',crntSc,singleScene.id)
                        try:
                            queue_inst, created = AiTask.objects.get_or_create(avatar_image=firstQueueData.multipleScene.avatar_image,avatar_sound=firstQueueData.multipleScene.avatar_sound,text=allScenes[crntSc]['text'])
                        except:
                            queue_inst = AiTask.objects.filter(avatar_image=firstQueueData.multipleScene.avatar_image,avatar_sound=firstQueueData.multipleScene.avatar_sound,text=allScenes[crntSc]['text'])
                            queue_inst.delete()
                            queue_inst, created = AiTask.objects.get_or_create(avatar_image=firstQueueData.multipleScene.avatar_image,avatar_sound=firstQueueData.multipleScene.avatar_sound,text=allScenes[crntSc]['text'])
                        
                        if queue_inst.text.strip() == '' or singleScene.videoThemeTemplate.name == "No Avatar":
                            print('Inside No Text')
                            queue_inst.status = 1
                            queue_inst.totalOutputFrame = 1
                            queue_inst.save()
                            avatar_inst = queue_inst.avatar_image

                            ## load first and last frame
                            try:
                                _ = allAvatarImgSeq[avatar_inst.id][0]
                            except:
                                allAvatarImgSeq[avatar_inst.id] = sorted(os.listdir(os.path.join(avatar_inst.getcwd(),'fullbody/without_swap/')))
                                
                            startFrameIndx = 0
                            aiStartFrame = queue_inst.start_frame
                            aiOutputFolder = queue_inst.getFaceSwapDir()
                            frame = os.path.join(avatar_inst.getcwd(),'fullbody/without_swap/',allAvatarImgSeq[avatar_inst.id][aiStartFrame+startFrameIndx])
                            print('Inside No Text',frame,os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.png'))
                            shutil.copy(frame,os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.png'))
                            if firstQueueData.isDefault == True and (singleScene.bgVideoType == 3 or singleScene.bgVideoType == 4):
                                t = extractBgFrame(singleScene.getBgVideoPath(),singleScene.getBgVideoSeq(),queue_inst.totalOutputFrame)
                           
                            currentProcessingFrame += queue_inst.totalOutputFrame
                            
                        elif queue_inst.status != 1:
                            print(f'Generating AI: {datetime.now()} {queue_inst.id} {firstQueueData.id}')
                            queue_inst.status = 2
                            queue_inst.save()

                            avatar_inst = queue_inst.avatar_image

                            isSound = queue_inst.generateSound()

                            avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY = queue_inst.getAiPosition()
                            avatarPosSize = avatarPosFX - avatarPosIX
                            


                            #load mask
                            aiVideoMask = cv2.VideoCapture(os.path.join(avatar_inst.getcwd(),'fullbody/mask.mp4'))
                            aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, queue_inst.start_frame)
                            

                            if isSound:
                                try:
                                    print(f'Started Wav2Lip: {datetime.now()} {queue_inst.id} {firstQueueData.id}')
                                    wav = audio.load_wav(os.path.join(queue_inst.getcwd(),'sound.wav'), 16000)
                                    mel = audio.melspectrogram(wav)

                                    if np.isnan(mel.reshape(-1)).sum() > 0:
                                        open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == {str(queue_inst.id)} == Wav2Lip == Mel contains nan!")
                                        queue_inst.output = json.dumps({"wav2lip": {"status": False,"message": 'Mel contains nan!'}})
                                        queue_inst.status = 0
                                        queue_inst.save()
                                        firstQueueData.status = 0
                                        firstQueueData.save()
                                        isErrorFlag = True
                                        break

                                    mel_chunks = []
                                    mel_idx_multiplier = 80./settings.VIDEO_DEFAULT_FPS 
                                    i = 0
                                    while 1:
                                        start_idx = int(i * mel_idx_multiplier)
                                        if start_idx + melstepsize > len(mel[0]):
                                            mel_chunks.append(mel[:, len(mel[0]) - melstepsize:])
                                            break
                                        mel_chunks.append(mel[:, start_idx : start_idx + melstepsize])
                                        i += 1
                                    mel_chunk_len = len(mel_chunks)

                                    queue_inst.totalOutputFrame = mel_chunk_len
                                    queue_inst.save()

                                    if firstQueueData.isDefault == True and (singleScene.bgVideoType == 3 or singleScene.bgVideoType == 4):
                                        print(f'Frame Extract: {datetime.now()} {queue_inst.id} {firstQueueData.id}')
                                        ct = Thread(target=extractBgFrame,args=(singleScene.getBgVideoPath(),singleScene.getBgVideoSeq(),queue_inst.totalOutputFrame,))
                                        ct.start()
                                        allThread.append(ct)

                                    ## load first and last frame
                                    try:
                                        _ = allAvatarImgSeq[avatar_inst.id][0]
                                    except:
                                        allAvatarImgSeq[avatar_inst.id] = sorted(os.listdir(os.path.join(avatar_inst.getcwd(),'fullbody/without_swap/')))


                                    drivingInit = torch.tensor(np.load(avatar_inst.getFirstInitFrame())).permute(0, 3, 1, 2).to(DEVICE)
                                    sourceFrame = torch.tensor(np.load(avatar_inst.getSourceFrame())).permute(0, 3, 1, 2).to(DEVICE)
                                    kpSourceFrame = settings.FIRSTORDERKPDETECTOR(sourceFrame)
                                    kpDrivingInit = settings.FIRSTORDERKPDETECTOR(drivingInit)

                                    startFrameIndx = 0
                                    aiStartFrame = queue_inst.start_frame
                                    aiOutputFolder = queue_inst.getFaceSwapDir()
                                    avatarMainFolder = os.path.join(avatar_inst.getcwd(),'fullbody/without_swap/')

                                    # remove existing avatar data
                                    try:
                                        os.system(f"rm -rf {aiOutputFolder}*")
                                    except:
                                        pass


                                    currentFrame = queue_inst.start_frame - 1

                                    wav2lip_data_generator = wav2lip_datagen(mel_chunks,avatar_inst.getWav2lipVideo(),avatar_inst.getFaceCordinate(),queue_inst.start_frame,queue_inst.avatar_image.totalFrames)
                                    wav2lipOutput = []
                                    currentMaxBatch = 3000
                                    for i, (img_batch, mel_batch, frames, coords) in enumerate(tqdm(wav2lip_data_generator,total=int(np.ceil(float(mel_chunk_len)/settings.WAVLIPBATCHSIZE)))):
                                        with torch.no_grad():
                                            img_batch = torch.FloatTensor(np.transpose(img_batch, (0, 3, 1, 2))).to(DEVICE)
                                            mel_batch = torch.FloatTensor(np.transpose(mel_batch, (0, 3, 1, 2))).to(DEVICE)
                                            pred = settings.WAVLIPMODEL(mel_batch, img_batch)
                                            pred = pred.cpu().numpy().transpose(0, 2, 3, 1) * 255.
                                            for p, f, c in zip(pred, frames, coords):
                                                y1, y2, x1, x2 = c
                                                p = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
                                                f[y1:y2, x1:x2] = p

                                                drivingData = cv2.resize(cv2.cvtColor(f,cv2.COLOR_BGR2RGB), (512,512))[..., :3].astype('float32')/255
                                                wav2lipOutput.append(drivingData)

                                        if len(wav2lipOutput)>currentMaxBatch:
                                            for drivingData in tqdm(wav2lipOutput,total=len(wav2lipOutput)):
                                                currentFrame += 1
                                                currentIndex = currentFrame%queue_inst.avatar_image.totalFrames
                                                with torch.no_grad():
                                                    drivingDataT = torch.tensor(drivingData[np.newaxis]).permute(0,3,1,2).to(DEVICE)
                                                    kpDriving = settings.FIRSTORDERKPDETECTOR(drivingDataT)
                                                    kpNorm = normalize_kp(kp_source=kpSourceFrame, kp_driving=kpDriving,
                                                                    kp_driving_initial=kpDrivingInit, use_relative_movement=True,
                                                                    use_relative_jacobian=True, adapt_movement_scale=True)
                                                    
                                                    fout = settings.FIRSTORDERGENERATOR(sourceFrame, kp_source=kpSourceFrame, kp_driving=kpNorm)
                                                    aiRGBFrame = img_as_ubyte(np.transpose(fout['prediction'].data.cpu().numpy(), [0, 2, 3, 1])[0])

                                                aiRGBAFrame = cv2.cvtColor(aiRGBFrame,cv2.COLOR_RGB2RGBA)

                                                if currentIndex == 0 and currentFrame!=0:
                                                    aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, currentIndex)
                                                ret,aiVideoMaskFrame = aiVideoMask.read()
                                                aiRGBAFrame[:,:,3] = aiVideoMaskFrame[:,:,1]
                                                aiRGBAFrame = cv2.resize(aiRGBAFrame,(avatarPosSize,avatarPosSize))
                                                if avatarPosIY<=0:
                                                    aiRGBAFrame = aiRGBAFrame[avatarPosIY:avatarPosFY,avatarPosIX:avatarPosFX]
                                                ctAiProcess = Thread(target=saveAiSwapFrame, args=(os.path.join(avatarMainFolder,allAvatarImgSeq[avatar_inst.id][currentIndex]),aiRGBAFrame,(avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY),os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.png'),))
                                                ctAiProcess.start()
                                                startFrameIndx+=1

                                                ## update progress in db
                                                if (currentProcessingFrame+startFrameIndx)%settings.VIDEO_PROGRESS_UPDATE_FRAME==0:
                                                    firstQueueData.updateProgress(currentProcessingFrame+startFrameIndx)

                                            wav2lipOutput = []
                                                    
                                    gc.collect()
                                    queue_inst.output = json.dumps({"wav2lip": {"status": True}})
                                    queue_inst.save()
                                    print(f'Wav2Lip Completed: {datetime.now()} {queue_inst.id} {firstQueueData.id}')

                                    if len(wav2lipOutput)>0:
                                        for drivingData in tqdm(wav2lipOutput,total=len(wav2lipOutput)):
                                            currentFrame += 1
                                            currentIndex = currentFrame%queue_inst.avatar_image.totalFrames
                                            with torch.no_grad():
                                                drivingDataT = torch.tensor(drivingData[np.newaxis]).permute(0,3,1,2).to(DEVICE)
                                                kpDriving = settings.FIRSTORDERKPDETECTOR(drivingDataT)
                                                kpNorm = normalize_kp(kp_source=kpSourceFrame, kp_driving=kpDriving,
                                                                kp_driving_initial=kpDrivingInit, use_relative_movement=True,
                                                                use_relative_jacobian=True, adapt_movement_scale=True)
                                                
                                                fout = settings.FIRSTORDERGENERATOR(sourceFrame, kp_source=kpSourceFrame, kp_driving=kpNorm)
                                                aiRGBFrame = img_as_ubyte(np.transpose(fout['prediction'].data.cpu().numpy(), [0, 2, 3, 1])[0])

                                            aiRGBAFrame = cv2.cvtColor(aiRGBFrame,cv2.COLOR_RGB2RGBA)
                                            if currentIndex == 0 and currentFrame!=0:
                                                aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, currentIndex)
                                            ret,aiVideoMaskFrame = aiVideoMask.read()
                                            aiRGBAFrame[:,:,3] = aiVideoMaskFrame[:,:,1]
                                            aiRGBAFrame = cv2.resize(aiRGBAFrame,(avatarPosSize,avatarPosSize))
                                            if avatarPosIY<=0:
                                                aiRGBAFrame = aiRGBAFrame[avatarPosIY:avatarPosFY,avatarPosIX:avatarPosFX]
                                            ctAiProcess = Thread(target=saveAiSwapFrame, args=(os.path.join(avatarMainFolder,allAvatarImgSeq[avatar_inst.id][currentIndex]),aiRGBAFrame,(avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY),os.path.join(aiOutputFolder,f'{str(startFrameIndx).zfill(5)}.png'),))
                                            ctAiProcess.start()
                                            startFrameIndx+=1

                                            ## update progress in db
                                            if (currentProcessingFrame+startFrameIndx)%settings.VIDEO_PROGRESS_UPDATE_FRAME==0:
                                                firstQueueData.updateProgress(currentProcessingFrame+startFrameIndx)
                                                

                                            #if (min(currentProcessingFrame/firstQueueData.totalFrames,1)*100)%
                                        gc.collect()
                                    aiVideoMask.release()
                                    allThread.append(ctAiProcess)
                                    queue_inst.status = 1
                                    queue_inst.output = json.dumps({"first_order": {"status": True}})
                                    queue_inst.save()

                                    currentProcessingFrame += queue_inst.totalOutputFrame
                                    firstQueueData.updateProgress(currentProcessingFrame)
                                    
                                except Exception as e:
                                    exc_type, exc_obj, exc_tb = sys.exc_info()
                                    open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == {str(queue_inst.id)} == {str(e)}  ==  {str(exc_tb.tb_lineno)} == {str(traceback.format_exc())}\n\n")
                                    queue_inst.output = json.dumps({"other": {"status": False,"message": str(e)}})
                                    queue_inst.status = 0
                                    queue_inst.save()
                                    firstQueueData.status = 0
                                    firstQueueData.save()
                                    isErrorFlag = True
                                    break
                            else:
                                print('Error in Sound')
                                open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == {str(queue_inst.id)} == Sound == Error in Generating TTS")
                                queue_inst.output = json.dumps({"sound": {"status": False,"message": "Error in Generating TTS"}})
                                queue_inst.status = 0
                                firstQueueData.status = 0
                                firstQueueData.save()
                                queue_inst.save()
                                isErrorFlag = True
                                break
                        else:

                            if firstQueueData.isDefault == True and (singleScene.bgVideoType == 3 or singleScene.bgVideoType == 4):
                                ct = Thread(target=extractBgFrame,args=(singleScene.getBgVideoPath(),singleScene.getBgVideoSeq(),queue_inst.totalOutputFrame,))
                                ct.start()
                                allThread.append(ct)
                            currentProcessingFrame += queue_inst.totalOutputFrame
                            firstQueueData.updateProgress(currentProcessingFrame)

                        uniqueData['scenes'][crntSc]['aitask'] = queue_inst.id
                        uniqueData['scenes'][crntSc]['totalAvatarFrames'] = queue_inst.totalOutputFrame

                    if isErrorFlag==False:
                        for currentThread in allThread:
                            currentThread.join()
                        uniqueData['id']=firstQueueData.id
                        uniqueData['isDefault']=firstQueueData.isDefault
                        rabbitMQSendJob('electronCanvasRender',json.dumps(uniqueData),durable=True)
                        firstQueueData.completedFrames = currentProcessingFrame
                        firstQueueData.totalFrames = currentProcessingFrame
                        firstQueueData.status = 3
                        #firstQueueData.output=firstQueueData.multipleScene.getUniqueData()
                        firstQueueData.save()
                        firstQueueData.updateProgress(currentProcessingFrame)

                        
                else:
                    #open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Query Not found == {str(traceback.format_exc())}\n\n")
                    time.sleep(5)
            except Exception as e:
                open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Try/Except Block == {str(traceback.format_exc())}\n\n")
                time.sleep(5)
    except KeyboardInterrupt:
        sys.exit()

