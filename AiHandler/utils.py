from django.conf import settings

if settings.LOAD_GPU_MODEL:

    import gc
    import torch
    import cv2,os
    import traceback
    import subprocess
    import numpy as np
    from tqdm import tqdm
    from threading import Thread
    from datetime import datetime
    from skimage import img_as_ubyte
    from AiHandler.wav2lip import audio
    from scipy.spatial import ConvexHull


    _AVATAR_IMAGE_SEQ = {}

    def normalize_kp(kp_source, kp_driving, kp_driving_initial, adapt_movement_scale=False,
                    use_relative_movement=False, use_relative_jacobian=False):
        if adapt_movement_scale:
            source_area = ConvexHull(kp_source['value'][0].data.cpu().numpy()).volume
            driving_area = ConvexHull(kp_driving_initial['value'][0].data.cpu().numpy()).volume
            adapt_movement_scale = np.sqrt(source_area) / np.sqrt(driving_area)
        else:
            adapt_movement_scale = 1

        kp_new = {k: v for k, v in kp_driving.items()}

        if use_relative_movement:
            kp_value_diff = (kp_driving['value'] - kp_driving_initial['value'])
            kp_value_diff *= adapt_movement_scale
            kp_new['value'] = kp_value_diff + kp_source['value']

            if use_relative_jacobian:
                jacobian_diff = torch.matmul(kp_driving['jacobian'], torch.inverse(kp_driving_initial['jacobian']))
                kp_new['jacobian'] = torch.matmul(jacobian_diff, kp_source['jacobian'])

        return kp_new

    def wav2lip_datagen(mels,video_path,face_cord_path,start_frame=0,totalFrames=3000,img_size=settings.WAVLIPIMAGESIZE,wav2lip_batch_size=settings.WAVLIPBATCHSIZE):
        img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []
        total_frames = len(mels)
        face_cord = np.load(open(face_cord_path,'rb'))[start_frame:start_frame+total_frames]
        video = cv2.VideoCapture(video_path)
        if start_frame>0:
            video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        tempFrame=None
        img_size_half = img_size//2
        currentFrame = start_frame - 1
        for i, m in enumerate(mels):
            currentFrame +=1
            currentIndex = currentFrame%totalFrames
            if currentIndex == 0 and currentFrame!=0:
                video.set(cv2.CAP_PROP_POS_FRAMES, currentIndex)
            is_frame, frame = video.read()
            if is_frame:
                tempFrame = frame
            x1,y1,x2,y2 = face_cord[currentIndex]

            img_batch.append(cv2.resize(tempFrame[y1:y2,x1:x2],(img_size,img_size)))
            mel_batch.append(m)
            frame_batch.append(tempFrame)
            coords_batch.append((y1, y2, x1, x2))

            if len(img_batch) >= wav2lip_batch_size:
                img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

                img_masked = img_batch.copy()
                img_masked[:, img_size_half:] = 0

                img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
                mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

                yield img_batch, mel_batch, frame_batch, coords_batch
                img_batch, mel_batch, frame_batch, coords_batch = [], [], [], []

        if len(img_batch) > 0:
            img_batch, mel_batch = np.asarray(img_batch), np.asarray(mel_batch)

            img_masked = img_batch.copy()
            img_masked[:, img_size_half:] = 0

            img_batch = np.concatenate((img_masked, img_batch), axis=3) / 255.
            mel_batch = np.reshape(mel_batch, [len(mel_batch), mel_batch.shape[1], mel_batch.shape[2], 1])

            yield img_batch, mel_batch, frame_batch, coords_batch

    def getMelChunks(audioPath,melstepsize = settings.WAVLIPMELSTEPSIZE):
        wav = audio.load_wav(audioPath, 16000)
        mel = audio.melspectrogram(wav)

        if np.isnan(mel.reshape(-1)).sum() > 0:
            return (False,"Mel contains nan!")

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
        return (True,mel_chunks)

    def getFfmpegPipeTransVideo(outputPath):
        #ffmpegPipeRGBA = [ 'ffmpeg','-y','-framerate','30','-f', 'rawvideo','-pix_fmt', 'rgba','-s', '512x512','-i', '-','-an','-vcodec', 'png', outputPath]
        ffmpegPipeRGBA = [ 'ffmpeg','-y','-framerate','30','-f', 'rawvideo','-pix_fmt', 'rgba','-s', '512x512','-i', '-','-an','-c:v','libvpx-vp9', outputPath]
        return subprocess.Popen(ffmpegPipeRGBA, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def getVideoGenerateConfig(queue_inst,mel_chunks=0,isVideoOutput=False):
        avatar_inst = queue_inst.avatar_image
        _imageSeqDir = avatar_inst.getImageSeqPath()
        ## load first and last frame
        try:
            _ = _AVATAR_IMAGE_SEQ[avatar_inst.id][0]
        except:
            _AVATAR_IMAGE_SEQ[avatar_inst.id] = sorted(os.listdir(_imageSeqDir))

        wav2lipConfig = {"batchSize": settings.WAVLIPBATCHSIZE,"mel_chunks": mel_chunks,"npFirstInitFrame": avatar_inst.getFirstInitFrame(),"npSourceFrame": avatar_inst.getSourceFrame(),"sourceVideo": avatar_inst.getWav2lipVideo(),"faceCoordinate": avatar_inst.getFaceCordinate()}
        avatarConfig = {"totalFrame": avatar_inst.totalFrames,"startFrame": queue_inst.start_frame,"videoMask": avatar_inst.getMaskPath(),"imageSeqDir": _imageSeqDir,"allImagesSeq": _AVATAR_IMAGE_SEQ[avatar_inst.id],"outputSeqDir": queue_inst.getImageSeqDir(),"position": avatar_inst.getAiPosition()}
        if isVideoOutput:
            avatarConfig["outputVideoPath"] = queue_inst.getAiVideoOutputPath()
        return (wav2lipConfig,avatarConfig,)

    def mainVideoGenerateWithVideo(wav2lipConfig,avatarConfig,DEVICE=settings.DEVICE):

        aiVideoMask = cv2.VideoCapture(avatarConfig["videoMask"])
        aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, avatarConfig["startFrame"])

        ffmpegPipe = getFfmpegPipeTransVideo(avatarConfig["outputVideoPath"])

        mel_chunks = wav2lipConfig["mel_chunks"]
        mel_chunk_len = len(mel_chunks)
        drivingInit = torch.tensor(np.load(wav2lipConfig["npFirstInitFrame"])).permute(0, 3, 1, 2).to(DEVICE)
        sourceFrame = torch.tensor(np.load(wav2lipConfig["npSourceFrame"])).permute(0, 3, 1, 2).to(DEVICE)
        kpSourceFrame = settings.FIRSTORDERKPDETECTOR(sourceFrame)
        kpDrivingInit = settings.FIRSTORDERKPDETECTOR(drivingInit)

        startFrameIndx = 0
        currentProcessingFrame = 0
        currentFrame  = avatarConfig["startFrame"] - 1
        
        wav2lip_data_generator = wav2lip_datagen(mel_chunks,wav2lipConfig["sourceVideo"],wav2lipConfig["faceCoordinate"],avatarConfig["startFrame"],avatarConfig["totalFrame"])
        wav2lipOutput = []
        currentMaxBatch = 3000
        totalEpoch = int(np.ceil(float(mel_chunk_len)/wav2lipConfig["batchSize"]))
        for i, (img_batch, mel_batch, frames, coords) in enumerate(tqdm(wav2lip_data_generator,total=totalEpoch)):
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

            if len(wav2lipOutput)>currentMaxBatch or (len(wav2lipOutput)>0 and totalEpoch == i+1):
                for drivingData in tqdm(wav2lipOutput,total=len(wav2lipOutput)):
                    currentFrame += 1
                    currentIndex = currentFrame%avatarConfig["totalFrame"]
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
                    

                    ffmpegPipe.stdin.write(aiRGBAFrame.tobytes())
                    startFrameIndx+=1

                    ## update progress in db
                    if (currentProcessingFrame+startFrameIndx)%settings.VIDEO_PROGRESS_UPDATE_FRAME==0:
                        #firstQueueData.updateProgress(currentProcessingFrame+startFrameIndx)
                        # update progress callback
                        pass


        ffmpegPipe.stdin.close()
        aiVideoMask.release()
        gc.collect()


    def saveAiSwapFrame(fullImgPath,rgba,cord,outputPath):
        try:
            bgra = cv2.cvtColor(rgba,cv2.COLOR_RGBA2BGRA)
            sourceImg = cv2.imread(fullImgPath,cv2.IMREAD_UNCHANGED)
            faceMask = cv2.cvtColor(bgra[:,:,3],cv2.COLOR_GRAY2BGR)/255
            aiFaceMask = np.uint8(sourceImg[cord[1]:cord[3],cord[0]:cord[2]][:,:,:3]*(1-faceMask))
            sourceImg[cord[1]:cord[3],cord[0]:cord[2]][:,:,:3] = np.array(np.add(np.uint8(bgra[:,:,:3]*faceMask),aiFaceMask),dtype='uint8')
            cv2.imwrite(outputPath,sourceImg,[cv2.IMWRITE_WEBP_QUALITY, 80])
        except:
            open('../logs/videoGenLog.txt','a').write(f"{datetime.now()}  == Swap Error == {str(traceback.format_exc())} == {fullImgPath} == {outputPath}\n\n")
        return 0


    def loggerFunction(progress):
        pass
        #_message = f"Current Progress: {progress}"

    def mainVideoGenerate(wav2lipConfig,avatarConfig,loggerFunction=loggerFunction,DEVICE=settings.DEVICE):

        avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY = avatarConfig['position']
        avatarPosSize = avatarPosFX - avatarPosIX
        faceSwapPath = avatarConfig["outputSeqDir"]
        imageSeqDir = avatarConfig["imageSeqDir"]
        crnAvatarImageSeq = avatarConfig["allImagesSeq"]

        aiVideoMask = cv2.VideoCapture(avatarConfig["videoMask"])
        aiVideoMask.set(cv2.CAP_PROP_POS_FRAMES, avatarConfig["startFrame"])

        mel_chunks = wav2lipConfig["mel_chunks"]
        mel_chunk_len = len(mel_chunks)
        drivingInit = torch.tensor(np.load(wav2lipConfig["npFirstInitFrame"])).permute(0, 3, 1, 2).to(DEVICE)
        sourceFrame = torch.tensor(np.load(wav2lipConfig["npSourceFrame"])).permute(0, 3, 1, 2).to(DEVICE)
        kpSourceFrame = settings.FIRSTORDERKPDETECTOR(sourceFrame)
        kpDrivingInit = settings.FIRSTORDERKPDETECTOR(drivingInit)

        startFrameIndx = 0
        currentProcessingFrame = 0
        currentFrame  = avatarConfig["startFrame"] - 1
        
        wav2lip_data_generator = wav2lip_datagen(mel_chunks,wav2lipConfig["sourceVideo"],wav2lipConfig["faceCoordinate"],avatarConfig["startFrame"],avatarConfig["totalFrame"])
        wav2lipOutput = []
        currentMaxBatch = 3000
        totalEpoch = int(np.ceil(float(mel_chunk_len)/wav2lipConfig["batchSize"]))
        for i, (img_batch, mel_batch, frames, coords) in enumerate(tqdm(wav2lip_data_generator,total=totalEpoch)):
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

            if len(wav2lipOutput)>currentMaxBatch or (len(wav2lipOutput)>0 and totalEpoch == i+1):
                for drivingData in tqdm(wav2lipOutput,total=len(wav2lipOutput)):
                    currentFrame += 1
                    currentIndex = currentFrame%avatarConfig["totalFrame"]
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
                    ctAiProcess = Thread(target=saveAiSwapFrame, args=(os.path.join(imageSeqDir,crnAvatarImageSeq[currentIndex]),aiRGBAFrame,(avatarPosIX,avatarPosIY,avatarPosFX,avatarPosFY),os.path.join(faceSwapPath,f'{str(startFrameIndx).zfill(5)}.webp'),))
                    ctAiProcess.start()

                    startFrameIndx+=1

                    ## update progress in db
                    if (currentProcessingFrame+startFrameIndx)%settings.VIDEO_PROGRESS_UPDATE_FRAME==0:
                        #firstQueueData.updateProgress(currentProcessingFrame+startFrameIndx)
                        # update progress callback
                        loggerFunction(currentProcessingFrame+startFrameIndx)

        aiVideoMask.release()
        gc.collect()

