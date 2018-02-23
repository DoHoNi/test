import cv2
import numpy as np
import os
class Timelette_dashboard:

    # Setting variables for dashboard in landscape format
    def set_l_value(self):
        self.fm = 'L'
        self.x_margin = 15
        self.y_margin = 20
        self.img_x = 240
        self.img_y = 135
        self.circle_r = 18
        self.circle_margin = 10
        self.text_margin = -2
        self.font = 0
        self.per_dash = 12
        self.row_num = 2

    #Setting variables for dashboard in Portrait format
    def set_p_value(self):
        self.fm = 'P'
        self.x_margin = 9
        self.y_margin = 20
        self.img_x = 163
        self.img_y = 290
        self.circle_r = 20
        self.circle_margin = 10
        self.text_margin = -2
        self.font = 0
        self.per_dash = 9
        self.row_num = 3

    #Overlaying an image file with an alpha value
    def add_alpha_image (self,back_img, target_img, x_offset,y_offset):
        y1,y2 = y_offset,y_offset+target_img.shape[0]
        x1,x2 = x_offset,x_offset+target_img.shape[1]
        alpha_s = target_img[:,:,3] / 255.0
        alpha_l = 1.0 - alpha_s

        for c in range(3):
            back_img[y1:y2,x1:x2,c]=(alpha_s*target_img[:,:,3] + alpha_l*back_img[y1:y2,x1:x2,c])


    # Read image file and return it as image object
    def get_img(self,img_name):
        if self.room_info["all_files"][img_name]["ext"] == 'jpg':
            real_img_name = self.room_info["all_files"][img_name][self.fm]
        else :
            real_img_name = self.room_info["all_files"][img_name]["iconic"][self.fm]
        img = cv2.imread(os.path.join(self.img_path,real_img_name),cv2.IMREAD_UNCHANGED)
        img = cv2.resize(img,(self.img_x,self.img_y))
        return img

    #Return location of image
    def get_img_path (self):
        print self.room_info["room_path"]
        print self.num_r
        self.basic_path = '/'.join(self.room_info["room_path"].split('/')[:-1])+'/basic'
        self.img_path = os.path.join(self.room_info["room_path"],"imgs")

    # Read black background image and retrun it as image object
    def get_black_img (self,timestamp):
        print "basic_path" ,self.basic_path
        back_img = cv2.imread(os.path.join(self.basic_path,"black.jpg"),cv2.IMREAD_UNCHANGED)
        back_img = np.resize(back_img, (950,525,3))
        self.dash_path = str(self.room_info["cur_manifest"])+"_"+str(self.num_r)+"_"+timestamp+"_dash.png"
        return back_img

    # Update all_file list to add new media files
    def update_all_data_files(self):
        print "update all data files"
        index_new_item = self.num_all_data_names 
        print index_new_item, len(self.room_info["all_files"])
        add_data_names = [i for i in self.room_info["all_files"] if not i in self.all_data_names]
        print add_data_names
        self.all_data_names = self.all_data_names + add_data_names
        print self.all_data_names
        self.num_all_data_names = len(self.all_data_names)
        self.my_cur_info["all_data_names"] = self.all_data_names

    # making dashboard
    def make_dashboard(self,timestamp):
        self.num_r = 0 
        timestamp = str(timestamp)

        #getting black background image
        back_img = self.get_black_img(timestamp)

        #update all data list
        if len(self.room_info["all_files"]) > self.num_all_data_names:
            self.update_all_data_files()
        print "num_all_Data_names : ",self.num_all_data_names

        #image overlay one by one
        for i in range(self.num_all_data_names):
            img = self.get_img(self.all_data_names[i])
            print i, img.shape[0]
            x_offset = self.x_margin*(((i%self.per_dash)%self.row_num)+1)+ self.img_x*((i%self.per_dash)%self.row_num)
            y_offset = self.y_margin*(((i%self.per_dash)/self.row_num)+1)+ self.img_y*((i%self.per_dash)/self.row_num)
            back_img[y_offset:y_offset+img.shape[0], x_offset:x_offset+img.shape[1]] = img[:,:,:]

            img_end_x = (self.img_x+self.x_margin) * (((i%self.per_dash)%self.row_num)+1)
            img_end_y = (self.img_y+self.y_margin) * (((i%self.per_dash)/self.row_num)+1)
            index = str(i+1)
            circle_coler = (255,0,0) if i<self.numimg else (0,0,225)
            text_margin = self.text_margin + 6*(len(index)-1)
            back_img = cv2.circle(back_img,(img_end_x - (self.circle_r+self.circle_margin),img_end_y - (self.circle_r+self.circle_margin)),self.circle_r+2,(255,255,255),-1)
            back_img = cv2.circle(back_img,(img_end_x - (self.circle_r+self.circle_margin),img_end_y - (self.circle_r+self.circle_margin)),self.circle_r,circle_coler,-1)
            back_img = cv2.putText(back_img,index,(img_end_x -(self.circle_r*2+text_margin),img_end_y-(self.circle_r+5)),self.font,0.6,(255,255,255),2,cv2.LINE_AA)

            #if the midea file is video, It add video icon and duration of the video
            if self.room_info["all_files"][self.all_data_names[i]]["ext"]== "mp4":
                video_x = x_offset+20
                video_y = y_offset+(self.img_y-10)
                self.add_alpha_image(back_img,self.video_img,video_x,video_y)
                duration = self.room_info["all_files"][self.all_data_names[i]]["duration"]
                time = '{0:02.0f}:{1:02.0f}'.format(*divmod(duration,60))
                back_img = cv2.putText(back_img,time,(video_x+30,video_y+15),self.font,0.4,(255,255,255),1,cv2.LINE_AA)

            # Save the dashboard when it is full
            if i%self.per_dash == self.per_dash-1:
                #dash_path = self.room_info["cur_manifest"]+"_"+str(self.num_r)+"_dash.png"
                cv2.imwrite(os.path.join(self.img_path,self.dash_path),back_img)
                self.my_cur_info["dashboard"].append(self.dash_path)
                self.num_r +=1
                back_img = self.get_black_img(timestamp)

        # Save the dashboard 
        if (self.num_all_data_names-1)%self.per_dash != self.per_dash-1:
            cv2.imwrite(os.path.join(self.img_path,self.dash_path),back_img)
            self.my_cur_info["dashboard"].append(self.dash_path)

        return self.my_cur_info


    def __init__(self,room_info=None,my_cur_info=None,fm=None):
        print "hello"
        #Setting variable
        self.num_r = 0
        self.room_info  = room_info
        self.my_cur_info = my_cur_info
        self.numimg = my_cur_info["numimg"]
        self.all_data_names = my_cur_info["all_data_names"]
        self.my_cur_info["dashboard"] = []
        self.num_all_data_names = len(my_cur_info["all_data_names"])
        print "all_data_names", my_cur_info["all_data_names"]
        self.get_img_path()
        self.video_img = cv2.imread(os.path.join(self.basic_path,"video.png"),-1)
        self.video_img = cv2.resize(self.video_img,(20,20))
        if fm == 'L':
            self.set_l_value()
        else :
            self.set_p_value()

