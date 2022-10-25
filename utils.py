def adjusted_img_size(img, ad):
    '''
    Recalculates the width and height of an image to fit within a given space.
    If either dimension exceeds the available space, the image will be shrunk to fit accordingly
    without affecting its aspect ratio. This will result in dead space if the aspect ratios of the
    two rectangles do not match.
    '''
    
    aratio = img.size[0] / img.size[1]  
    ew = aratio * ad[1]          # Estimated width if full available height is to be used
    eh = ad[0] / aratio          # Estimated height if full available width is to be used
    ew = int(min(ew, ad[0]))
    eh = int(min(eh, ad[1]))
    
    return ew, eh