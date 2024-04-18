
def getAvatarCoordinate(prsCategory, prsPosition, avatarConfig):
    avatarWidth = 1080
    if (prsCategory == 0):
        if (prsPosition == 0):
            return avatarConfig["FM"]
        elif (prsPosition == 1):
            ww = avatarWidth * avatarConfig["FM"]["scale"]
            return {"ax": (1920 - ww) / 2, "ay": avatarConfig["FM"]["ay"], "scale": avatarConfig["FM"]["scale"] }
        elif (prsPosition == 2):
            ww = avatarWidth * avatarConfig["FM"]["scale"]
            return {"ax": (1920 - ww) - avatarConfig["FM"]["ax"], "ay": avatarConfig["FM"]["ay"], "scale": avatarConfig["FM"]["scale"] }
        elif (prsPosition == 3):
            return avatarConfig["FB"]
        elif (prsPosition == 4):
            ww = avatarWidth * avatarConfig["FB"]["scale"]
            return {"ax": (1920 - ww) / 2, "ay": avatarConfig["FB"]["ay"], "scale": avatarConfig["FB"]["scale"] }
        elif (prsPosition == 5):
            ww = avatarWidth * avatarConfig["FB"]["scale"]
            return {"ax": (1920 - ww) - avatarConfig["FB"]["ax"], "ay": avatarConfig["FB"]["ay"], "scale": avatarConfig["FB"]["scale"] }
        else:
            return avatarConfig["FM"]

    else:
        if (prsPosition == 0):
            return avatarConfig["SM"]
        elif (prsPosition == 1):
            movedBy = (1920 - avatarConfig["SM"]["size"]) / 2 - avatarConfig["SM"]["x"]
            return {"ax": avatarConfig["SM"]["ax"] + movedBy, "ay": avatarConfig["SM"]["ay"], "x": avatarConfig["SM"]["x"] + movedBy, "y": avatarConfig["SM"]["y"], "scale": avatarConfig["SM"]["scale"], "size": avatarConfig["SM"]["size"], "anX": avatarConfig["SM"]["anX"], "anY": avatarConfig["SM"]["anY"], "anSc": avatarConfig["SM"]["anSc"] }
        elif (prsPosition == 2):
            movedBy = (1920 - 2 * avatarConfig["SM"]["x"] - avatarConfig["SM"]["size"])
            return {"ax": avatarConfig["SM"]["ax"] + movedBy, "ay": avatarConfig["SM"]["ay"], "x": avatarConfig["SM"]["x"] + movedBy, "y": avatarConfig["SM"]["y"], "scale": avatarConfig["SM"]["scale"], "size": avatarConfig["SM"]["size"], "anX": avatarConfig["SM"]["anX"], "anY": avatarConfig["SM"]["anY"], "anSc": avatarConfig["SM"]["anSc"] }
        elif (prsPosition == 3):
            return avatarConfig["SB"]
        elif (prsPosition == 4):
            movedBy = (1920 - avatarConfig["SB"]["size"]) / 2 - avatarConfig["SB"]["x"]
            return {"ax": avatarConfig["SB"]["ax"] + movedBy, "ay": avatarConfig["SB"]["ay"], "x": avatarConfig["SB"]["x"] + movedBy, "y": avatarConfig["SB"]["y"], "scale": avatarConfig["SB"]["scale"], "size": avatarConfig["SB"]["size"], "anX": avatarConfig["SB"]["anX"], "anY": avatarConfig["SB"]["anY"], "anSc": avatarConfig["SB"]["anSc"] }
        elif (prsPosition == 5):
            movedBy = (1920 - 2 * avatarConfig["SB"]["x"] - avatarConfig["SB"]["size"])
            return {"ax": avatarConfig["SB"]["ax"] + movedBy, "ay": avatarConfig["SB"]["ay"], "x": avatarConfig["SB"]["x"] + movedBy, "y": avatarConfig["SB"]["y"], "scale": avatarConfig["SB"]["scale"], "size": avatarConfig["SB"]["size"], "anX": avatarConfig["SB"]["anX"], "anY": avatarConfig["SB"]["anY"], "anSc": avatarConfig["SB"]["anSc"] }
        else:
            return avatarConfig["SM"]
