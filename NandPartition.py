
import os
import re
import subprocess

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element,SubElement, Comment,tostring
from xml.dom import minidom


import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
from matplotlib.figure import Figure

class NandPartition(tk.Tk):
    def __init__(self, *args, **kargs):
        tk.Tk.__init__(self,*args,**kargs)
        # tk.Tk.iconbitmap(self, default="nand.icon")
        tk.Tk.wm_title(self, "Nand partition")
        
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight = 1)
        container.grid_columnconfigure(0, weight = 1)
        
        
        self.create_menubar(container)
        self.pie= NandPie(container,self)
        
    def create_menubar(self,container):
        menubar = tk.Menu(container)
        
        fileMenu = tk.Menu(menubar,tearoff=0)
        fileMenu.add_command(label="Read by adb",command=lambda: self.read_by_adb())
        fileMenu.add_command(label="Load from xml",command=lambda:self.load_from_xml())
        # fileMenu.add_command(label="Save picture",command=lambda:self.save_picture())
        menubar.add_cascade(label= "File",menu=fileMenu)
        
        
        tk.Tk.config(self,menu=menubar)
    def get_partition_start_and_size(self):
        partition_list=[]
        for part in range(1,100):
            cmd=["adb", "shell","cat /sys/block/mmcblk0/mmcblk0p{}/start".format(part)]
            result = subprocess.run(cmd,stdout=subprocess.PIPE)
            data=result.stdout.decode()
            try:
                start = int(data)
            except Exception as e:
                break
            cmd=["adb", "shell","cat /sys/block/mmcblk0/mmcblk0p{}/size".format(part)]
            result = subprocess.run(cmd,stdout=subprocess.PIPE)
            data=result.stdout.decode()
            try:
                size= int(data)
            except Exception as e:
                break
            cmd=["adb", "shell","cat /sys/block/mmcblk0/mmcblk0p{}/uevent|grep PARTNAME".format(part)]
            result = subprocess.run(cmd,stdout=subprocess.PIPE)
            data=result.stdout.decode()
            name=data.replace("PARTNAME=","")
            partition_list.append([name.strip(),start,size])
        return partition_list
    def read_by_adb(self):
        cmd=["adb", "shell","cat /proc/mtd"]
        result = subprocess.run(cmd,stdout=subprocess.PIPE)
        pattern = re.compile("mtd(\d+):\s+(\w+)\s+(\w+)\s+\"(\w+)\"")
        data=result.stdout.decode()
        result = pattern.findall(data)
        # print(result)
        print("read by adb")
        if result != []:
            self.pie.update_mtd(result)
            return
        print("try /proc/partitions")
        partitions = self.get_partition_start_and_size()
        if partitions != []:
            self.pie.update_partition(partitions)
            return
        print("Not read data from device")
    def load_from_xml(self):
        print("load from xml")
        xml_file = filedialog.askopenfilename(initialdir="/",title="Select partition xml",filetype=[("xml file","rawprogram0.xml")])
        print(xml_file)
        root = ET.parse(xml_file)
        
        # Create Iterator
        iter = root.getiterator()
        partitions = []
        for element in iter:
            if element.tag == "program":
                part={}
                for name,value in element.items():
                    part[name]=value
                if "BackupGPT" != part["label"] and "PrimaryGPT" != part["label"]:
                    partitions.append([part["label"],int(part["start_sector"]),int(part["num_partition_sectors"])])
        if partitions != []:
            self.pie.update_partition(partitions)
            return
    def save_picture(self):
        print("save picture")

class NandPie(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        self.figure = Figure(figsize=(6,6),dpi = 100)
        self.pie = self.figure.add_subplot(1,2,1)
        self.table = self.figure.add_subplot(1,2,2)
        labels = ["Full"]
        sizes  = [100]
        self.pie.plot([1,2,3,4,5,6,7,8],[5,6,1,2,8,9,3,5])
        canvas = FigureCanvasTkAgg(self.figure,self)
        self.canvas = canvas
        canvas.get_tk_widget().pack(side=tk.TOP, fill= tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas,self)
        toolbar.update()
        canvas._tkcanvas.pack(side=tk.TOP, fill = tk.BOTH, expand= True)
        self.grid(row = 0, column = 0 , sticky = "nsew")
        self.tkraise()
    def update_mtd(self,data):
        labels = []
        labels_legend=[]
        sizes  = []
        cell_text=[]
        for partition in data:
            sizeOne = int(partition[1],16)
            blocksize=int(partition[2],16)
            label = partition[3]
            sizes.append(sizeOne)
            labels.append(label)
            cell_text.append([label,str(int(sizeOne/blocksize))])
            
            labels_legend.append(label)
        print(labels)
        print(sizes)
        self.pie.clear()
        # patches,texts,texts1   = self.pie.pie(sizes,labels=labels,autopct='%1.1f%%',labeldistance=1.1,rotatelabels =True)
        patches,texts = self.pie.pie(sizes)
        # print(len(patches))
        
        # print(patches)
        # print(texts)
        self.pie.legend(patches,labels_legend, loc= "best", bbox_to_anchor=(0,1.),fontsize=8)
        
        self.table.table(cellText=cell_text, colLabels=["name","Blocks"],loc="center")
        self.table.axis('off')
        self.canvas.draw()
    def update_partition(self, data):
        self.pie.clear()
        self.table.clear()
        labels = []
        sizes = []
        cellText = []
        total_size=0
        last_size=0
        last_start=0
        for part in data:
            name=part[0]
            start=int(part[1])
            size=int(part[2])
            skip = start - last_start - last_size
            if last_size != 0 and start != last_size+last_start:
                print("Detect skip before {} {} blocks".format(name,start-last_size-last_start))
            sizes.append(size)
            labels.append(name)
            cellText.append([name,start,size/2,str(skip) + "({:.0f}M)".format( skip*512/1024/1024)])
            total_size=total_size + size
            last_start = start
            last_size  = size
        patches, texts=self.pie.pie(sizes)
        self.pie.set_title("Total Emmc size is {}M".format(total_size))
        self.pie.legend(patches,labels,loc="best",bbox_to_anchor=(0,1.),fontsize=8)
        self.table.table(cellText=cellText, colLabels=['Partition',"start_sector",'Size(kb)','Skip'],loc="center")
        self.table.axis('off')
        
        self.canvas.draw()
app = NandPartition()
app.geometry("1024x768")
app.mainloop()
