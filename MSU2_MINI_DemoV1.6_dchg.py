#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import json  # 用于保存json格式配置
import os  # 用于读取文件
import queue  # geezmo: 流水线同步和交换数据用
import sys
import threading  # 引入多线程支持
import time  # 引入延时库
import tkinter as tk  # 引入UI库
import tkinter.filedialog  # 用于获取文件路径
import tkinter.messagebox
import traceback
from ctypes import windll
from datetime import datetime, timedelta  # 用于获取当前时间
from tkinter import ttk  # geezmo: 好看的皮肤

import numpy as np  # 使用numpy加速数据处理
import psutil  # 引入psutil获取设备信息（需要额外安装）
import pystray
import serial  # 引入串口库（需要额外安装）
import serial.tools.list_ports
from mss import mss  # geezmo: 快速截图
from PIL import Image, ImageDraw, ImageTk  # 引入PIL库进行图像处理

import MSU2_MINI_MG_minimark as MiniMark
from MSU2_MINI_MG_minimark import MiniMarkParser

# import pyautogui  # 用于截图(需要额外安装pillow) geezmo: 已去除依赖


# 使用高dpi缩放适配高分屏
try:  # >= win 8.1
    windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
except:  # win 8.0 or less
    windll.user32.SetProcessDPIAware()

# 颜色对应的RGB565编码
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
WHITE = 0xFFFF
BLACK = 0x0000
YELLOW = 0xFFE0
GRAY0 = 0xEF7D
GRAY1 = 0x8410
GRAY2 = 0x4208

Img_data_use = bytearray()  # 空数组
size_USE_X1 = 160
size_USE_Y1 = 80

# SHOW_WIDTH = 160  # 画布宽度
# SHOW_HEIGHT = 80  # 画布高度

imagefiletypes = [
    ("Image file", "*.jpg"),
    ("Image file", "*.jpeg"),
    ("Image file", "*.png"),
    ("Image file", "*.bmp"),
    ("Image file", "*.ico"),
    ("Image file", "*.webp"),
    ("Image file", "*.jfif"),
    ("Image file", "*.jpe"),
    ("Image file", "*.tiff"),
    ("Image file", "*.tif"),
    ("Image file", "*.dib"),
]


def insert_disabled_text(item, text, clean=True):
    item.config(state=tk.NORMAL)
    if clean:
        item.delete("1.0", tk.END)  # 清除文本框
    item.insert(tk.END, text)
    item.config(state=tk.DISABLED)


def convertImageFileToRGB(file_path):
    global Text1
    img_data = bytearray()
    if not os.path.exists(file_path):  # 检查文件是否存在
        insert_disabled_text(Text1, "文件不存在：%s\n" % file_path, False)
        return img_data  # 如果文件不存在，直接返回，不执行后续代码

    try:
        im1 = Image.open(file_path)
    except Exception as e:
        errstr = "图片\"%s\"打开失败：%s\n" % (file_path, e)
        print(errstr)
        insert_disabled_text(Text1, errstr, False)
        return img_data
    if im1.width >= (im1.height * 2):  # 图片长宽比例超过2:1
        im2 = im1.resize((int(80 * im1.width / im1.height), 80))
        Img_m = int(im2.width / 2)
        box = (Img_m - 80, 0, Img_m + 80, 80)  # 定义需要裁剪的空间
        im2 = im2.crop(box)
    else:
        im2 = im1.resize((160, int(160 * im1.height / im1.width)))
        Img_m = int(im2.height / 2)
        box = (0, Img_m - 40, 160, Img_m + 40)  # 定义需要裁剪的空间
        im2 = im2.crop(box)
    im2 = im2.convert("RGB")  # 转换为RGB格式
    for y in range(0, 80):  # 逐字解析编码
        for x in range(0, 160):  # 逐字解析编码
            r, g, b = im2.getpixel((x, y))
            img_data.append(((r >> 3) << 3) | (g >> 5))
            img_data.append((((g % 32) >> 2) << 5) | (b >> 3))
    return img_data


# 按键功能定义
def Get_Photo_Path1():  # 获取文件路径
    global photo_path1, Label3
    photo_path = tk.filedialog.askopenfilename(title="选择文件", filetypes=imagefiletypes)
    if photo_path != "" and photo_path != photo_path1:
        photo_path1 = photo_path
        insert_disabled_text(Label3, photo_path1)


def Get_Photo_Path2():  # 获取文件路径
    global photo_path2, Label4
    photo_path = tk.filedialog.askopenfilename(title="选择文件", filetypes=[("Bin file", "*.bin")])
    if photo_path != "" and photo_path != photo_path2:
        photo_path2 = photo_path
        insert_disabled_text(Label4, photo_path2)


def Get_Photo_Path3():  # 获取文件路径
    global photo_path3, Label5  # 支持JPG、PNG、BMP图像格式
    photo_path = tk.filedialog.askopenfilename(title="选择文件", filetypes=imagefiletypes)
    if photo_path != "" and photo_path != photo_path3:
        photo_path3 = photo_path
        insert_disabled_text(Label5, photo_path3)


def Get_Photo_Path4():  # 获取文件路径
    global photo_path4, Label6
    photo_path = tk.filedialog.askopenfilename(title="选择文件", filetypes=imagefiletypes)
    if photo_path != "" and photo_path != photo_path4:
        photo_path4 = photo_path
        insert_disabled_text(Label6, photo_path4)


def Write_Photo_Path1():  # 写入文件
    global photo_path1, write_path_index, Text1, Img_data_use
    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_disabled_text(Text1, "有正在执行的任务%d，写入失败\n" % write_path_index, False)
        return
    if photo_path1 == "":
        insert_disabled_text(Text1, "Path1 is None\n", False)
        return

    insert_disabled_text(Text1, "图像格式转换...\n")
    Img_data_use = convertImageFileToRGB(photo_path1)
    write_path_index = 1


def Write_Photo_Path2():  # 写入文件
    global photo_path2, write_path_index, Text1
    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_disabled_text(Text1, "有正在执行的任务%d，写入失败\n" % write_path_index, False)
        return
    if photo_path2 == "":
        insert_disabled_text(Text1, "Path2 is None\n", False)
        return

    insert_disabled_text(Text1, "准备烧写Flash固件...\n")
    write_path_index = 2


def Write_Photo_Path3():  # 写入文件
    global photo_path3, write_path_index, Text1, Img_data_use
    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_disabled_text(Text1, "有正在执行的任务%d，转换失败\n" % write_path_index, False)
        return
    if photo_path3 == "":
        insert_disabled_text(Text1, "Path3 is None\n", False)
        return

    insert_disabled_text(Text1, "图像格式转换...\n")
    Img_data_use = convertImageFileToRGB(photo_path3)
    write_path_index = 3


def Write_Photo_Path4():  # 写入文件
    global photo_path4, write_path_index, Text1, Img_data_use
    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_disabled_text(Text1, "有正在执行的任务%d，转换失败\n" % write_path_index, False)
        return
    if photo_path4 == "":
        insert_disabled_text(Text1, "Path4 is None\n", False)
        return

    insert_disabled_text(Text1, "动图格式转换中...\n")
    Path_use = photo_path4
    try:
        index = Path_use.rindex(".")
    except ValueError:
        insert_disabled_text(Text1, "动图名称不符合要求！\n", False)
        return  # 如果文件名不符合要求，直接返回
    path_file_type = Path_use[index:]
    Path_use = Path_use[:index - 1]

    Img_data_use = bytearray()
    u_time = time.time()
    for i in range(0, 36):  # 依次转换36张图片
        file_path = "%s%d%s" % (Path_use, i, path_file_type)
        Img_data_use = Img_data_use + convertImageFileToRGB(file_path)

    insert_disabled_text(Text1, "转换完成，耗时%.3f秒\n" % (time.time() - u_time), False)
    write_path_index = 4


def Page_UP():  # 上一页
    global State_change, machine_model
    if machine_model == 3903:
        machine_model = 0
    elif machine_model == 5:
        machine_model = 3901
    else:
        machine_model = machine_model + 1
    State_change = 1
    print("Current model changed to: %s" % machine_model)


def Page_Down():  # 下一页
    global State_change, machine_model
    if machine_model == 3901:
        machine_model = 5
    elif machine_model == 0:
        machine_model = 3903
    else:
        machine_model = machine_model - 1
    State_change = 1
    print("Current model changed to: %s" % machine_model)


def LCD_Change():  # 切换显示方向
    global LCD_Change_use, Device_State
    if Device_State == 0:
        print("设备未连接，切换失败")
        return
    if LCD_Change_use == 0:  # 0
        LCD_Change_use = 1
    else:  # 1
        LCD_Change_use = 0


def SER_Write(Data_U0):
    global ser
    if not ser.is_open:
        print("设备未连接，取消发送")
        return
    try:  # 尝试发出指令,有两种无法正确发送命令的情况：1.设备被移除,发送出错；2.设备处于MSN连接状态，对于电脑发送的指令响应迟缓
        # ser.reset_input_buffer()
        ser.write(Data_U0)
        ser.flush()
    except Exception as e:  # 出现异常
        print("发送异常, %s" % traceback.format_exc())
        ser.close()  # 先将异常的串口连接关闭，防止无法打开
        set_device_state(0)  # 出现异常，串口需要重连


def SER_Read():
    global ser
    if not ser.is_open:
        print("设备未连接，取消读取")
        return 0
    try:  # 尝试获取数据
        trytimes = 500000  # 尝试次数计数，防止一直获取不到数据
        recv = ser.read(ser.in_waiting)
        while recv != 0 and len(recv) == 0 and trytimes > 0:
            recv = ser.read(ser.in_waiting)
            trytimes -= 1
        if trytimes == 0:
            print("SER_Read timeout")
        return recv
    except Exception as e:  # 出现异常
        print("接收异常, %s" % traceback.format_exc())
        ser.close()  # 先将异常的串口连接关闭，防止无法打开
        set_device_state(0)
        return 0


def Read_M_u8(add):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(0 * 32)  # 识别为8bit SFR读
    hex_use.append(add // 256)  # 高地址
    hex_use.append(add % 256)  # 低地址
    hex_use.append(0)  # 数值
    SER_Write(hex_use)  # 发出指令

    # 等待收回信息
    recv = SER_Read()  # .decode("byte")#获取串口数据
    if recv != 0 and len(recv) > 5:
        return recv[5]
    else:
        print("Read_M_u8 failed")
        set_device_state(0)
        return 0


def Read_M_u16(add):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(1 * 32)  # 识别为16bit SFR读
    hex_use.append(add % 256)  # 地址
    hex_use.append(0)  # 高位数值
    hex_use.append(0)  # 低位数值
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("gbk")#获取串口数据
    if recv != 0 and len(recv) > 5:
        return recv[4] * 256 + recv[5]
    else:
        print("Read_M_u16 failed")
        set_device_state(0)
        return 0


def Write_M_u8(add, data_w):  # 修改主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(4 * 32)  # 识别为16bit SFR写
    hex_use.append(add // 256)  # 高地址
    hex_use.append(add % 256)  # 低地址
    hex_use.append(data_w % 256)  # 数值
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 0:
        return 1
    else:
        print("Write_M_u8 failed")
        set_device_state(0)
        return 0


def Write_M_u16(add, data_w):  # 修改主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(1 * 32)  # 识别为16bit SFR写
    hex_use.append(add % 256)  # 地址
    hex_use.append(data_w // 256)  # 高位数值
    hex_use.append(data_w % 256)  # 低位数值
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("gbk")#获取串口数据
    if recv != 0 and len(recv) > 0:
        return 1
    else:
        print("Write_M_u16 failed")
        set_device_state(0)
        return 0


def Read_ADC_CH(ch):  # 读取主机ADC寄存器数值（ADC通道）
    hex_use = bytearray()  # 空数组
    hex_use.append(8)  # 读取ADC
    hex_use.append(ch)  # 通道
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("gbk")#获取串口数据
    if recv != 0 and len(recv) > 5 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return recv[4] * 256 + recv[5]
    else:
        print("Read_ADC_CH failed, will reconnect")
        set_device_state(0)
        return 0


# SFR格式：data_name data_unit data_family data_data
def Read_M_SFR_Data(add):  # 从u8区域获取SFR描述
    SFR_data = bytearray()  # 空数组
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        SFR_data.append(Read_M_u8(add + i))  # 读取编码数据
    data_type = 0  # 根据是否为0进行类型循环统计
    data_len = 0
    data_use = bytearray()  # 空数组
    data_name = b""
    data_unit = b""
    data_family = b""
    data_data = b""
    My_MSN_Data = []
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        if data_type < 3:
            if SFR_data[i] != 0:  # 未检测到0
                data_use.append(SFR_data[i])  # 将非0数据合并到一块
                continue
            if len(data_use) == 0:  # 没有接收到数据时就接收到00
                break  # 检测到0后收集的数据为空，判断为结束
            if data_type == 0:
                data_name = data_use  # 名称
                data_use = bytearray()  # 空数组
                data_type = 1
            elif data_type == 1:
                data_unit = data_use  # 单位
                data_use = bytearray()  # 空数组
                data_type = 2
            else:  # data_type == 2
                data_family = data_use  # 类型
                data_use = bytearray()  # 空数组
                data_type = 3
                data_len = ord(data_family) // 32
                if data_len == 0:  # u8 data 2B add
                    data_len = 2
                elif data_len == 1:  # u16 data 1B add
                    data_len = 1
                elif data_len == 2:  # u32 data 2B add
                    data_len = 2
                elif data_len == 3:  # u8 Text XB data
                    data_len = data_family[0] % 32  # 计算数据长度
        else:  # data_type == 3
            if data_len > 0:  # 正式的有效数据
                data_use.append(SFR_data[i])  # 将非0数据合并到一块
                data_len = data_len - 1
            if data_len == 0:  # 将后续数据收集完整，注意这儿不能用elif
                data_data = data_use
                # 对数据进行登记
                My_MSN_Data.append(MSN_Data(data_name, data_unit, data_family, data_data))

                data_type = 0  # 重置类型
                data_use = bytearray()  # 获取完成，重置数组
    return My_MSN_Data


def Print_MSN_Data(My_MSN_Data):
    type_list = ["u8_SFR地址", "u16_SFR地址", "u32_SFR地址", "字符串  ", "u8数组数据"]
    num = len(My_MSN_Data)
    print("MSN数据总数为：%d" % num)
    # 进行数据解析
    for i in range(0, num):  # 将数据全部打印出来
        data_str = "序号：%-5d名称：%-15s单位：%-20s类型：%-12s长度：%-5d地址：%-5s" % (
            i, My_MSN_Data[i].name.decode("gbk"), My_MSN_Data[i].unit, type_list[ord(My_MSN_Data[i].family) // 32],
            ord(My_MSN_Data[i].family) % 32, int.from_bytes(My_MSN_Data[i].data, byteorder="big"))
        print(data_str)


def Read_MSN_Data(My_MSN_Data):  # 读取MSN_data中的数据
    print("MSN_data:")
    for i in range(0, len(My_MSN_Data)):  # 将数据查找一遍
        use_data = []  # 创建一个空列表
        data_type = ord(My_MSN_Data[i].family) // 32
        if data_type == 0:  # 数据类型为u8地址(16bit)
            sfr_add = int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1])
            for n in range(0, ord(My_MSN_Data[i].family) % 32):
                use_data.append(Read_M_u8(sfr_add + n))
        elif data_type == 1:  # 数据类型为u16地址(8bit)
            use_data.append(Read_M_u16(int(My_MSN_Data[i].data[0])))
        elif data_type == 2:  # 数据类型为u32地址(16bit)
            sfr_add = int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1])
            for n in range(0, ord(My_MSN_Data[i].family) % 32):
                use_data.append(Read_M_u8(sfr_add + n))
        elif data_type == 3:  # 数据类型为u8字符串
            use_data.append(My_MSN_Data[i].data)
        elif data_type == 4:  # 数据类型为u8数组
            use_data.append(My_MSN_Data[i].data)
        print("%-10s = %s" % (My_MSN_Data[i].name.decode("gbk"), use_data))


def Write_MSN_Data(My_MSN_Data, name_use, data_w):  # 在MSN_data写入数据
    for i in range(0, len(My_MSN_Data)):  # 将数据查找一遍
        if My_MSN_Data[i].name != name_use:
            continue
        data_type = int(My_MSN_Data[i].family) // 32
        if data_type == 0:  # 数据类型为u8地址(16bit)
            Write_M_u8(int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1]), data_w)
            print("\"%s\"写入%s完成" % (name_use, str(data_w)))
            return 1
        elif data_type == 1:  # 数据类型为u16地址(8bit)
            Write_M_u16(int(My_MSN_Data[i].data[0]), data_w)
            print("\"%s\"写入%s完成" % (name_use, str(data_w)))
            return 1
    print("\"%s\"不存在,请检查名称是否正确" % name_use)
    return 0


def Write_Flash_Page(Page_add, data_w, Page_num):  # 往Flash指定页写入256B数据
    # 先把数据传输完成
    hex_use = bytearray()  # 空数组
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use.append(4)  # 多次写入Flash
        hex_use.append(i)  # 低位地址
        hex_use.append(data_w[i * 4 + 0])  # Data0
        hex_use.append(data_w[i * 4 + 1])  # Data1
        hex_use.append(data_w[i * 4 + 2])  # Data2
        hex_use.append(data_w[i * 4 + 3])  # Data3
    hex_use.append(3)  # 对Flash操作
    hex_use.append(1)  # 写Flash
    hex_use.append(Page_add // 65536)  # Data0
    hex_use.append((Page_add % 65536) // 256)  # Data1
    hex_use.append((Page_add % 65536) % 256)  # Data2
    hex_use.append(Page_num % 256)  # Data3
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 0:
        return 1
    else:
        print("Write_Flash_Page failed")
        set_device_state(0)
        return 0


# 未经过擦除，直接往Flash指定页写入256B数据
def Write_Flash_Page_fast(Page_add, data_w, Page_num):
    # 先把数据传输完成
    hex_use = bytearray()
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use.append(4)  # 多次写入Flash
        hex_use.append(i)  # 低位地址
        hex_use.append(data_w[i * 4 + 0])  # Data0
        hex_use.append(data_w[i * 4 + 1])  # Data1
        hex_use.append(data_w[i * 4 + 2])  # Data2
        hex_use.append(data_w[i * 4 + 3])  # Data3
    hex_use.append(3)  # 对Flash操作
    hex_use.append(3)  # 经过擦除，写Flash
    hex_use.append(Page_add // (256 * 256))  # Data0
    hex_use.append((Page_add % 65536) // 256)  # Data1
    hex_use.append((Page_add % 65536) % 256)  # Data2
    hex_use.append(Page_num)  # Data3
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 0:
        return 1
    else:
        print("Write_Flash_Page_fast failed")
        set_device_state(0)
        return 0


def Erase_Flash_page(add, size):  # 清空指定区域的内存
    hex_use = bytearray()  # 空数组
    hex_use.append(3)  # 对Flash操作
    hex_use.append(2)  # 清空指定区域的内存
    hex_use.append((add % 65536) // 256)  # Data1
    hex_use.append((add % 65536) % 256)  # Data2
    hex_use.append((size % 65536) // 256)  # Data1
    hex_use.append((size % 65536) % 256)  # Data2
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 0:
        return 1
    else:
        print("Erase_Flash_page failed")
        set_device_state(0)
        return 0


def Read_Flash_byte(add):  # 读取指定地址的数值
    hex_use = bytearray()  # 空数组
    hex_use.append(3)  # 对Flash操作
    hex_use.append(0)  # 读Flash
    hex_use.append(add // (256 * 256))  # Data0
    hex_use.append((add % 65536) // 256)  # Data1
    hex_use.append((add % 65536) % 256)  # Data2
    hex_use.append(0)  # Data3
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 5:
        return recv[5]
    else:
        print("Read_Flash_byte failed")
        set_device_state(0)
        return 0


def Write_Flash_Photo_fast(Page_add, filepath):  # 往Flash里面写入Bin格式的照片
    global Text1
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件\"%s\", %s" % (filepath, traceback.format_exc()))
        insert_disabled_text(Text1, "文件路径或格式出错!\n", False)
        return 0
    Fsize = os.path.getsize(filepath)
    print("找到\"%s\"文件,大小：%dB" % (filepath, Fsize))
    insert_disabled_text(Text1, "大小%dB,烧录中...\n" % Fsize, False)
    u_time = time.time()
    # 进行擦除
    if Fsize % 256 != 0:
        Erase_Flash_page(Page_add, Fsize // 256 + 1)  # 清空指定区域的内存
    else:
        Erase_Flash_page(Page_add, Fsize // 256)  # 清空指定区域的内存

    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = binfile.read(256)
        Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page_fast(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    u_time = time.time() - u_time
    print("%s 烧写完成，耗时%.3f秒" % (filepath, u_time))
    insert_disabled_text(Text1, "烧写完成，耗时%.3f秒\n" % u_time, False)
    return 1


def Write_Flash_hex_fast(Page_add, img_use):  # 往Flash里面写入hex数据
    global Text1
    Fsize = len(img_use)
    if Fsize == 0:
        insert_disabled_text(Text1, "未读到数据，取消烧录。\n", False)
        return 0
    insert_disabled_text(Text1, "大小%dB,烧录中...\n" % Fsize, False)
    u_time = time.time()
    # 进行擦除
    if Fsize % 256 != 0:
        Erase_Flash_page(Page_add, Fsize // 256 + 1)  # 清空指定区域的内存
    else:
        Erase_Flash_page(Page_add, Fsize // 256)  # 清空指定区域的内存
    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = img_use[:256]  # 取前256字节
        img_use = img_use[256:]  # 取剩余字节
        Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = img_use  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page_fast(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    insert_disabled_text(Text1, "烧写完成，耗时%.3f秒\n" % (time.time() - u_time), False)
    return 1


def Write_Flash_ZK(Page_add, ZK_name):  # 往Flash里面写入Bin格式的字库
    filepath = "%s.bin" % ZK_name  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件\"%s\", %s" % (filepath, traceback.format_exc()))
        return 0
    Fsize = os.path.getsize(filepath) - 6  # 字库文件的最后六个字节不是点阵信息
    print("找到\"%s\"文件,大小：%dB" % (filepath, Fsize))
    for i in range(0, Fsize // 256):  # 每次写入一个Pag
        Fdata = binfile.read(256)
        Write_Flash_Page(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    print("%s 烧写完成" % filepath)
    return 1


def LCD_Set_XY(LCD_D0, LCD_D1):  # 设置起始位置
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(0)  # 设置起始位置
    hex_use.append(LCD_D0 // 256)  # Data0
    hex_use.append(LCD_D0 % 256)  # Data1
    hex_use.append(LCD_D1 // 256)  # Data2
    hex_use.append(LCD_D1 % 256)  # Data3
    SER_Write(hex_use)  # 发出指令


def LCD_Set_Size(LCD_D0, LCD_D1):  # 设置大小
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(1)  # 设置大小
    hex_use.append(LCD_D0 // 256)  # Data0
    hex_use.append(LCD_D0 % 256)  # Data1
    hex_use.append(LCD_D1 // 256)  # Data2
    hex_use.append(LCD_D1 % 256)  # Data3
    SER_Write(hex_use)  # 发出指令


def LCD_Set_Color(LCD_D0, LCD_D1):  # 设置颜色（FC,BC）
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(2)  # 设置颜色
    hex_use.append(LCD_D0 // 256)  # Data0
    hex_use.append(LCD_D0 % 256)  # Data1
    hex_use.append(LCD_D1 // 256)  # Data2
    hex_use.append(LCD_D1 % 256)  # Data3
    SER_Write(hex_use)  # 发出指令


def LCD_Photo(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(0)  # 显示彩色图片
    hex_use.append(Page_Add // 256)
    hex_use.append(Page_Add % 256)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_Photo failed")
        set_device_state(0)
        return 0


def LCD_ADD(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(7)  # 载入地址
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_ADD failed")
        set_device_state(0)
        return 0


def LCD_State(LCD_S):
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(10)  # 载入地址
    hex_use.append(LCD_S)
    hex_use.append(0)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 5 and recv[0] == hex_use[0] and recv[1] == hex_use[1] and recv[3] == LCD_S:
        print("LCD towards change to %d" % LCD_S)
        return 1
    else:
        print("LCD towards change failed %d" % LCD_S)
        set_device_state(0)
        return 0


def LCD_DATA(data_w, size):  # 往LCD写入指定大小的数据
    # 先把数据传输完成
    hex_use = bytearray()
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use.append(4)  # 多次写入Flash
        hex_use.append(i)  # 低位地址
        hex_use.append(data_w[i * 4 + 0])  # Data0
        hex_use.append(data_w[i * 4 + 1])  # Data1
        hex_use.append(data_w[i * 4 + 2])  # Data2
        hex_use.append(data_w[i * 4 + 3])  # Data3
    hex_use.append(2)  # 对Flash操作
    hex_use.append(3)  # 经过擦除，写Flash
    hex_use.append(8)  # Data0
    hex_use.append(size // 256)  # Data1
    hex_use.append(size % 256)  # Data2
    hex_use.append(0)  # Data3
    SER_Write(hex_use)  # 发出指令


# 往Flash里面写入Bin格式的照片
def Write_LCD_Photo_fast(x_star, y_star, x_size, y_size, Photo_name):
    filepath = "%s.bin" % Photo_name  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件\"%s\", %s" % (filepath, traceback.format_exc()))
        return 0
    Fsize = os.path.getsize(filepath)
    print("找到\"%s\"文件,大小：%dB" % (filepath, Fsize))
    u_time = time.time()
    # 进行地址写入
    LCD_ADD(x_star, y_star, x_size, y_size)
    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = binfile.read(256)
        LCD_DATA(Fdata, 256)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        LCD_DATA(Fdata, Fsize % 256)  # (page,数据，大小)
    u_time = time.time() - u_time
    print("%s 显示完成，耗时%.3f秒" % (filepath, u_time))
    return 1


# 往Flash里面写入Bin格式的照片
def Write_LCD_Photo_fast1(x_star, y_star, x_size, y_size, Photo_name):
    filepath = "%s.bin" % Photo_name  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件\"%s\", %s" % (filepath, traceback.format_exc()))
        return 0
    Fsize = os.path.getsize(filepath)
    print("找到\"%s\"文件,大小：%dB" % (filepath, Fsize))
    u_time = time.time()
    # 进行地址写入
    LCD_ADD(x_star, y_star, x_size, y_size)
    hex_use = bytearray()  # 空数组
    for j in range(0, Fsize // 256):  # 每次写入一个Page
        data_w = binfile.read(256)
        # 先把数据格式转换好
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        data_w = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            # 不足位置补充0xFF
            data_w = data_w + int(255).to_bytes(1, byteorder="little")
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(Fsize % 256)
        hex_use.append(0)
    hex_use.append(2)
    hex_use.append(3)
    hex_use.append(9)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    u_time = time.time() - u_time
    print("%s 显示完成，耗时%.3f秒" % (filepath, u_time))
    return 1


# 往Flash里面写入Bin格式的照片
def Write_LCD_Screen_fast(x_star, y_star, x_size, y_size, Photo_data):
    LCD_ADD(x_star, y_star, x_size, y_size)
    Photo_data_use = Photo_data
    hex_use = bytearray()  # 空数组
    for j in range(0, x_size * y_size * 2 // 256):  # 每次写入一个Page
        data_w = Photo_data_use[:256]
        Photo_data_use = Photo_data_use[256:]
        cmp_use = []  # 空数组,
        for i in range(0, 64):  # 256字节数据分为64个指令
            cmp_use.append(
                data_w[i * 4 + 0] * 256 * 256 * 256
                + data_w[i * 4 + 1] * 256 * 256
                + data_w[i * 4 + 2] * 256
                + data_w[i * 4 + 3]
            )
        result = max(set(cmp_use), key=cmp_use.count)  # 统计出现最多的数据
        hex_use.append(2)
        hex_use.append(4)
        color_ram = result
        hex_use.append(color_ram // (256 * 256 * 256))
        color_ram = color_ram % (256 * 256 * 256)
        hex_use.append(color_ram // (256 * 256))
        color_ram = color_ram % (256 * 256)
        hex_use.append(color_ram // 256)
        hex_use.append(color_ram % 256)
        # 先把数据格式转换好
        for i in range(0, 64):  # 256字节数据分为64个指令
            if (data_w[i * 4 + 0] * 256 * 256 * 256
                + data_w[i * 4 + 1] * 256 * 256
                + data_w[i * 4 + 2] * 256
                + data_w[i * 4 + 3]
            ) != result:  #
                hex_use.append(4)
                hex_use.append(i)
                hex_use.append(data_w[i * 4 + 0])
                hex_use.append(data_w[i * 4 + 1])
                hex_use.append(data_w[i * 4 + 2])
                hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if (x_size * y_size * 2) % 256 != 0:  # 还存在没写完的数据
        data_w = Photo_data_use  # 将剩下的数据读完
        for i in range(x_size * y_size * 2 % 256, 256):
            data_w.append(0xFF)  # 不足位置补充0xFF
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(x_size * y_size * 2 % 256)
        hex_use.append(0)
    SER_Write(hex_use)  # 发出指令


# 往Flash里面写入Bin格式的照片，对发送的数据进行编码分析,缩短数据指令
def Write_LCD_Screen_fast1(x_star, y_star, x_size, y_size, Photo_data):
    LCD_ADD(x_star, y_star, x_size, y_size)
    Photo_data_use = Photo_data
    hex_use = bytearray()  # 空数组
    for j in range(0, x_size * y_size * 2 // 256):  # 每次写入一个Page
        data_w = Photo_data_use[:256]
        Photo_data_use = Photo_data_use[256:]
        # 先把数据格式转换好
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if (x_size * y_size * 2) % 256 != 0:  # 还存在没写完的数据
        data_w = Photo_data_use  # 将剩下的数据读完
        for i in range(x_size * y_size * 2 % 256, 256):
            data_w.append(0xFF)  # 不足位置补充0xFF
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(x_size * y_size * 2 % 256)
        hex_use.append(0)
    # 等待传输完成
    hex_use.append(2)
    hex_use.append(3)
    hex_use.append(9)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令


def LCD_Photo_wb(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add, LCD_FC, LCD_BC):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    LCD_Set_Color(LCD_FC, LCD_BC)
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(1)  # 显示单色图片
    hex_use.append(Page_Add // 256)
    hex_use.append(Page_Add % 256)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_Photo_wb failed")
        set_device_state(0)  # 接收出错
        return 0


def LCD_ASCII_32X64(LCD_X, LCD_Y, Txt, LCD_FC, LCD_BC, Num_Page):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, LCD_BC)
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(2)  # 显示ASCII
    hex_use.append(ord(Txt))
    hex_use.append(Num_Page // 256)
    hex_use.append(Num_Page % 256)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_ASCII_32X64 failed")
        set_device_state(0)  # 接收出错
        return 0


def LCD_GB2312_16X16(LCD_X, LCD_Y, Txt, LCD_FC, LCD_BC):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, LCD_BC)
    Txt_Data = Txt.encode("gb2312")
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(3)  # 显示彩色图片
    hex_use.append(Txt_Data[0])
    hex_use.append(Txt_Data[1])
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_GB2312_16X16 failed")
        set_device_state(0)  # 接收出错
        return 0


def LCD_Photo_wb_MIX(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add, LCD_FC, BG_Page):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    LCD_Set_Color(LCD_FC, BG_Page)
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(4)  # 显示单色图片
    hex_use.append(Page_Add // 256)
    hex_use.append(Page_Add % 256)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_Photo_wb_MIX failed")
        set_device_state(0)  # 接收出错
        return 0


def LCD_ASCII_32X64_MIX(LCD_X, LCD_Y, Txt, LCD_FC, BG_Page, Num_Page):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, BG_Page)
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(5)  # 显示ASCII
    hex_use.append(ord(Txt))
    hex_use.append(Num_Page // 256)
    hex_use.append(Num_Page % 256)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_ASCII_32X64_MIX failed")
        set_device_state(0)  # 接收出错
        return 0


def LCD_GB2312_16X16_MIX(LCD_X, LCD_Y, Txt, LCD_FC, BG_Page):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, BG_Page)
    Txt_Data = Txt.encode("gb2312")
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(6)  # 显示彩色图片
    hex_use.append(Txt_Data[0])
    hex_use.append(Txt_Data[1])
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_GB2312_16X16_MIX failed")
        set_device_state(0)  # 接收出错
        return 0


# 对指定区域进行颜色填充
def LCD_Color_set(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, F_Color):
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(11)  # 显示彩色图片
    hex_use.append(F_Color // 256)
    hex_use.append(F_Color % 256)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv != 0 and len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_Color_set failed")
        set_device_state(0)  # 接收出错
        return 0


def show_gif():  # 显示GIF动图
    global State_change, gif_num
    if State_change == 1:
        State_change = 0
        gif_num = 0
    if gif_num > 35:
        gif_num = 0

    LCD_Photo(0, 0, 160, 80, gif_num * 100)
    gif_num = gif_num + 1
    time.sleep(0.05)  # 用来调整动图播放速度


disk_io_counter = psutil.disk_io_counters()
net_io_counter = psutil.net_io_counters()


def show_PC_state(FC, BC):  # 显示PC状态
    global State_change, disk_io_counter, net_io_counter
    photo_add = 4038
    num_add = 4026
    if State_change == 1:
        State_change = 0
        LCD_Photo_wb(0, 0, 160, 80, photo_add, FC, BC)  # 放置背景

    # CPU
    CPU = int(psutil.cpu_percent(interval=0.5))
    # mem
    mem = psutil.virtual_memory()
    RAM = int(mem.percent)

    # battery
    battery = psutil.sensors_battery()
    if battery is not None:
        BAT = int(battery.percent)
    else:
        BAT = 100
    # 磁盘使用率
    disk_info = psutil.disk_usage("/")
    FRQ = int(disk_info.used * 100 / disk_info.total)

    # # 磁盘IO
    # FRQ = 0
    # disk_io_counter_cur = psutil.disk_io_counters()
    # disk_used = (disk_io_counter_cur.read_bytes + disk_io_counter_cur.write_bytes
    #              - disk_io_counter.read_bytes - disk_io_counter.write_bytes)
    # if disk_used > 0:
    #     FRQ = disk_used // 1024 // 1024  # MB
    # disk_io_counter = disk_io_counter_cur
    # # 网络IO
    # BAT = 0
    # net_io_counter_cur = psutil.net_io_counters()
    # net_used = (net_io_counter_cur.bytes_sent + net_io_counter_cur.bytes_recv
    #             - net_io_counter.bytes_sent - net_io_counter.bytes_recv)
    # if net_used > 0:
    #     BAT = net_used * 8 // 1024 // 1024  # Mb
    # net_io_counter = net_io_counter_cur

    if CPU >= 100:
        LCD_Photo_wb(24, 0, 8, 33, 10 + num_add, FC, BC)
        CPU = CPU % 100
    else:
        LCD_Photo_wb(24, 0, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(32, 0, 24, 33, (CPU // 10) + num_add, FC, BC)
    LCD_Photo_wb(56, 0, 24, 33, (CPU % 10) + num_add, FC, BC)
    if RAM >= 100:
        LCD_Photo_wb(104, 0, 8, 33, 10 + num_add, FC, BC)
        RAM = RAM % 100
    else:
        LCD_Photo_wb(104, 0, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(112, 0, 24, 33, (RAM // 10) + num_add, FC, BC)
    LCD_Photo_wb(136, 0, 24, 33, (RAM % 10) + num_add, FC, BC)
    if BAT >= 100:
        LCD_Photo_wb(104, 47, 8, 33, 10 + num_add, FC, BC)
        BAT = BAT % 100
    else:
        LCD_Photo_wb(104, 47, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(112, 47, 24, 33, (BAT // 10) + num_add, FC, BC)
    LCD_Photo_wb(136, 47, 24, 33, (BAT % 10) + num_add, FC, BC)
    if FRQ >= 100:
        LCD_Photo_wb(24, 47, 8, 33, 10 + num_add, FC, BC)
        FRQ = FRQ % 100
    else:
        LCD_Photo_wb(24, 47, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(32, 47, 24, 33, (FRQ // 10) + num_add, FC, BC)
    LCD_Photo_wb(56, 47, 24, 33, (FRQ % 10) + num_add, FC, BC)
    time.sleep(0.3)  # 1秒左右刷新一次


def show_Photo1():  # 显示照片
    global State_change
    if State_change == 1:
        State_change = 0

    LCD_Photo(0, 0, 160, 80, 3926)  # 放置背景
    time.sleep(1)  # 1秒刷新一次


def show_PC_time():
    global State_change, current_time, color_use
    FC = color_use
    photo_add = 3826
    num_add = 3651
    if State_change == 1:
        State_change = 0
        LCD_Photo(0, 0, 160, 80, photo_add)  # 放置背景
        LCD_ASCII_32X64_MIX(56 + 8, 0, ":", FC, photo_add, num_add)
        # LCD_ASCII_32X64_MIX(136+8,32,":",FC,photo_add,num_add)

    time_h = int(current_time.hour)
    time_m = int(current_time.minute)
    time_S = int(current_time.second)
    LCD_ASCII_32X64_MIX(0 + 8, 8, chr((time_h // 10) + 48), FC, photo_add, num_add)
    LCD_ASCII_32X64_MIX(32 + 8, 8, chr((time_h % 10) + 48), FC, photo_add, num_add)
    LCD_ASCII_32X64_MIX(80 + 8, 8, chr((time_m // 10) + 48), FC, photo_add, num_add)
    LCD_ASCII_32X64_MIX(112 + 8, 8, chr((time_m % 10) + 48), FC, photo_add, num_add)
    # LCD_ASCII_32X64_MIX(160 + 8, 8, chr((time_S // 10) + 48), FC, photo_add, num_add)
    # LCD_ASCII_32X64_MIX(192 + 8, 8, chr((time_S % 10) + 48), FC, photo_add, num_add)
    time.sleep(1)  # 1秒刷新一次


def digit_to_ints(di):
    return [(di >> 24) & 0xFF, (di >> 16) & 0xFF, (di >> 8) & 0xFF, di & 0xFF]


def Screen_Date_Process(Photo_data):  # 对数据进行转换处理
    uint16_data = Photo_data.astype(np.uint32)
    hex_use = bytearray()  # 空数组
    total_data_size = size_USE_X1 * size_USE_Y1
    data_per_page = 128
    for j in range(0, total_data_size // data_per_page):  # 每次写入一个Page
        data_w = uint16_data[j * data_per_page: (j + 1) * data_per_page]
        cmp_use = data_w[::2] << 16 | data_w[1::2]  # 256字节数据分为64个指令

        result = 0
        if data_w.size > 0:
            u, c = np.unique(cmp_use, return_counts=True)
            result = u[c.argmax()]  # 找最频繁的指令

        hex_use.extend([2, 4])

        # 最常见的指令，背景色？
        hex_use.extend(digit_to_ints(result))
        # 每个前景色
        for i, cmp_value in enumerate(cmp_use):
            if cmp_value != result:
                hex_use.extend([4, i] + digit_to_ints(cmp_value))

        # Append footer
        hex_use.extend([2, 3, 8, 1, 0, 0])
    remaining_data_size = total_data_size % data_per_page
    if remaining_data_size != 0:  # 还存在没写完的数据
        data_w = uint16_data[-remaining_data_size:]  # 取最后的没有写的
        data_w += b"\xff\xff" * (128 - remaining_data_size)  # 补全128个 uint16
        cmp_use = data_w[::2] << 16 | data_w[1::2]
        for i in range(0, 64):
            cmp_value = cmp_use[i]
            hex_use.extend([4, i] + digit_to_ints(cmp_value))
        hex_use.extend([2, 3, 8, 0, remaining_data_size * 2, 0])
    return hex_use


def rgb888_to_rgb565(rgb888_array):
    # Convert RGB888 to RGB565
    r = (rgb888_array[:, :, 0] >> 3) & 0x1F  # 5 bits for red
    g = (rgb888_array[:, :, 1] >> 2) & 0x3F  # 6 bits for green
    b = (rgb888_array[:, :, 2] >> 3) & 0x1F  # 5 bits for blue

    r = r.astype(np.uint16)
    g = g.astype(np.uint16)
    b = b.astype(np.uint16)

    # Combine into RGB565 format
    rgb565 = (r << 11) | (g << 5) | b

    # Convert to a 16-bit unsigned integer array
    return rgb565.astype(np.uint16)


def shrink_image_block_average(image, shrink_factor):
    """
    图像每一块多次采样，最后平均

    Parameters:
    image (numpy.ndarray): The input image as a 2D (grayscale) or 3D (color) numpy array.
    shrink_factor (float): The factor by which the image dimensions are reduced.

    Returns:
    numpy.ndarray: The shrunk image.
    """

    # Calculate the new shape
    new_shape = (int(image.shape[0] / shrink_factor), int(image.shape[1] / shrink_factor))

    shrunk_parts = []
    # 4倍多重采样
    for rand in [(0.0, 0.0), (0.25, 0.5), (0.5, 0.25), (0.75, 0.75)]:
        start = (shrink_factor * rand[0], shrink_factor * rand[1])
        stop = (start[0] + image.shape[0] - 1, start[1] + image.shape[1] - 1)
        row_indices = np.round(np.linspace(start[0], stop[0] - shrink_factor, new_shape[0])).astype(np.uint32)
        col_indices = np.round(np.linspace(start[1], stop[1] - shrink_factor, new_shape[1])).astype(np.uint32)

        # Handle color and grayscale images
        if image.ndim == 3:
            shrunk_image = image[np.ix_(row_indices, col_indices, np.arange(image.shape[2]))]
        else:
            shrunk_image = image[np.ix_(row_indices, col_indices)]
        shrunk_parts.append(shrunk_image)

    return np.mean(shrunk_parts, axis=0, dtype=np.uint32)

    # 下面的算法可以用（每块所有像素平均），但是慢，所以用上面的简单算法，取少数几个点
    # # Calculate integer block size for averaging
    # block_size = int(np.floor(shrink_factor))
    #
    # # Calculate the shape after block averaging
    # new_shape = (image.shape[0] // block_size, image.shape[1] // block_size)
    #
    # # Perform block averaging
    # if image.ndim == 3:  # Color image
    #     averaged_image = (image.reshape(new_shape[0], block_size, new_shape[1], block_size, image.shape[2])
    #                       .mean(axis=(1, 3), dtype=np.uint32))
    # else:  # Grayscale image
    #     averaged_image = (image.reshape(new_shape[0], block_size, new_shape[1], block_size)
    #                       .mean(axis=(1, 3), dtype=np.uint32))
    #
    # # Nearest neighbor interpolation to handle fractional part
    # final_shape = (int(image.shape[0] / shrink_factor), int(image.shape[1] / shrink_factor))
    #
    # row_indices = np.round(np.linspace(0, averaged_image.shape[0] - 1, final_shape[0])).astype(np.uint32)
    # col_indices = np.round(np.linspace(0, averaged_image.shape[1] - 1, final_shape[1])).astype(np.uint32)
    #
    # # Handle color and grayscale images
    # if image.ndim == 3:
    #     shrunk_image = averaged_image[np.ix_(row_indices, col_indices, np.arange(image.shape[2]))].astype(np.uint8)
    # else:
    #     shrunk_image = averaged_image[np.ix_(row_indices, col_indices)].astype(np.uint8)
    # return shrunk_image


screen_shot_queue = queue.Queue(2)
screen_process_queue = queue.Queue(2)
screenshot_monitor_id = 1
cropped_monitor = {}
screenshot_region = (None, None, None, None)


def screen_shot_task():  # 创建专门的函数来获取屏幕图像和处理转换数据
    global MG_screen_thread_running, machine_model, screen_shot_queue, cropped_monitor
    print("截图线程创建成功")

    with mss() as sct:
        while MG_screen_thread_running:
            if machine_model != 5:
                if not screen_shot_queue.empty():  # 清空缓存，防止显示旧的窗口
                    screen_shot_queue.get()
                time.sleep(0.5)  # 不需要截图时
                continue
            if screen_shot_queue.full():
                time.sleep(1.0 / screenshot_limit_fps)  # 队列满时暂停一个周期
                continue

            try:
                sct_img = sct.grab(cropped_monitor)  # geezmo: 截屏已优化
                screen_shot_queue.put((sct_img, cropped_monitor), timeout=3)
            except queue.Full:
                # 每1s检测一次退出，并且如果下游不拿走，则重新截图
                pass
            except Exception as e:
                print("截屏失败 %s" % traceback.format_exc())

    # stop
    print("stop screenshot")


# geezmo: 流水线 第二步 处理图像
def screen_process_task():
    global MG_screen_thread_running, machine_model, screen_process_queue, screenshot_limit_fps, screen_shot_queue
    while MG_screen_thread_running:
        if machine_model != 5:
            if not screen_process_queue.empty():  # 清空缓存，防止显示旧的窗口
                screen_process_queue.get()
            time.sleep(0.5)  # 不需要截图时
            continue
        if screen_process_queue.full():
            time.sleep(1.0 / screenshot_limit_fps)  # 队列满时暂停一个周期
            continue

        try:
            sct_img, monitor = screen_shot_queue.get(timeout=3)
        except queue.Empty:
            continue

        bgra = np.frombuffer(sct_img.bgra, dtype=np.uint8).reshape((sct_img.size[1], sct_img.size[0], 4))
        rgb = bgra[:, :, :3]
        rgb = rgb[:, :, ::-1]

        if monitor["width"] <= monitor["height"] * 2:  # 横向充满
            im1 = shrink_image_block_average(rgb, rgb.shape[1] / size_USE_X1)
            im1 = im1[0: size_USE_Y1, :]
        else:  # 纵向充满
            im1 = shrink_image_block_average(rgb, rgb.shape[0] / size_USE_Y1)
            im1 = im1[:, 0: size_USE_X1]

        rgb888 = np.asarray(im1)

        rgb565 = rgb888_to_rgb565(rgb888)
        # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
        hexstream = Screen_Date_Process(rgb565.flatten())

        try:
            screen_process_queue.put(hexstream, timeout=3)
        except queue.Full:
            pass

    # stop
    print("stop screen process")


current_time = datetime.now()
screenshot_test_time = current_time
screenshot_last_limit_time = screenshot_test_time
screenshot_test_frame = 0
screenshot_limit_fps = 100
wait_time = 0.0


# 连续多次截图失败，重启截图线程
def screenshot_panic():
    global MG_screen_thread_running, screen_shot_thread, screen_process_thread
    MG_screen_thread_running = False
    print("Screenshot threads are panicking")
    if screen_shot_thread.is_alive():
        screen_shot_thread.join()
    if screen_process_thread.is_alive():
        screen_process_thread.join()
    MG_screen_thread_running = True
    screen_shot_thread.start()
    screen_process_thread.start()


def show_PC_Screen():  # 显示照片
    global State_change, Screen_Error, screenshot_test_frame, current_time, screen_process_queue
    global screenshot_test_time, screenshot_last_limit_time, wait_time, screenshot_limit_fps
    if State_change == 1:
        State_change = 0
        Screen_Error = 0
        LCD_ADD(0, 0, size_USE_X1, size_USE_Y1)

    try:
        hexstream = screen_process_queue.get(timeout=1)
    except queue.Empty:
        Screen_Error = Screen_Error + 1
        time.sleep(0.05)  # 防止频繁重试
        if Screen_Error > 100:
            screenshot_panic()
            Screen_Error = 0
        return
    SER_Write(hexstream)

    elapse_time = (current_time - screenshot_last_limit_time).total_seconds()
    if elapse_time > 5:  # 有切换，重置参数
        wait_time = 0
        screenshot_test_time = current_time
        screenshot_test_frame = 0
        elapse_time = 1.0 / screenshot_limit_fps  # 第一次不需要wait
    elif screenshot_test_frame % screenshot_limit_fps == 0:
        # 测试用：显示帧率
        # real_fps = screenshot_limit_fps / ((current_time - screenshot_test_time).total_seconds())
        # print("串流FPS: %s" % real_fps)
        screenshot_test_time = current_time
    wait_time += 1.0 / screenshot_limit_fps - elapse_time
    if wait_time > 0:
        time.sleep(wait_time)  # 精确控制FPS
    screenshot_last_limit_time = current_time
    screenshot_test_frame += 1
    if Screen_Error != 0:
        Screen_Error = 0


netspeed_last_refresh_time = None
netspeed_last_refresh_snetio = None
netspeed_plot_data = None


def sizeof_fmt(num, suffix="B", base=1024.0):
    # Use KB for small value
    for unit in ("K", "M", "G", "T", "P", "E", "Z"):
        num /= base
        if abs(num) < base:
            return "%3.1f%s%s" % (num, unit, suffix)
    return "%3.1fY%s" % (num, suffix)


def show_netspeed(text_color=(255, 128, 0)):
    global netspeed_last_refresh_time, netspeed_last_refresh_snetio, netspeed_plot_data
    global default_font, netspeed_font, State_change, wait_time, current_time

    bar_width = 2  # 每个点宽度
    image_height = 20  # 高度

    current_snetio = psutil.net_io_counters()
    # geezmo: 预渲染图片，显示网速
    if State_change == 1:
        # 初始化
        if netspeed_plot_data is None:
            netspeed_plot_data = [{"sent": 0, "recv": 0}] * (size_USE_X1 // bar_width)
        State_change = 0
        wait_time = 0
        netspeed_last_refresh_time = current_time - timedelta(seconds=0.001)
        netspeed_last_refresh_snetio = current_snetio
        LCD_ADD(0, 0, size_USE_X1, size_USE_Y1)

    # 获取网速 bytes/second

    seconds_elapsed = (current_time - netspeed_last_refresh_time) / timedelta(seconds=1)

    sent_per_second = (current_snetio.bytes_sent - netspeed_last_refresh_snetio.bytes_sent) / seconds_elapsed
    recv_per_second = (current_snetio.bytes_recv - netspeed_last_refresh_snetio.bytes_recv) / seconds_elapsed

    netspeed_plot_data = netspeed_plot_data[1:] + [{"sent": sent_per_second, "recv": recv_per_second}]

    netspeed_last_refresh_time = current_time
    netspeed_last_refresh_snetio = current_snetio

    # 绘制图片
    im1 = Image.new("RGB", (size_USE_X1, size_USE_Y1), (0, 0, 0))
    draw = ImageDraw.Draw(im1)

    # 绘制文字
    text = "上传%10s" % sizeof_fmt(sent_per_second)
    draw.text((0, 0), text, fill=text_color, font=default_font)
    text = "下载%10s" % sizeof_fmt(recv_per_second)
    draw.text((0, size_USE_Y1 / 2), text, fill=text_color, font=default_font)

    # 绘图
    for start_y, key, color in zip([19, 59], ["sent", "recv"], [(235, 139, 139), (146, 211, 217)]):
        sent_values = [data[key] for data in netspeed_plot_data]
        max_value = max(1024 * 100, max(sent_values))  # 最小范围 100KB/s

        for i, sent in enumerate(sent_values[-int(size_USE_X1 / bar_width):]):
            # Scale the sent value to the image height
            bar_height = int(sent * image_height / max_value) if max_value else 0
            x0 = i * bar_width
            y0 = image_height - bar_height
            x1 = (i + 1) * bar_width
            y1 = image_height

            # Draw the bar
            draw.rectangle([x0, start_y + y0, x1 - 1, max(start_y + y0, start_y + y1 - 1)], fill=color)

    rgb888 = np.asarray(im1)
    rgb565 = rgb888_to_rgb565(rgb888)
    # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
    hexstream = Screen_Date_Process(rgb565.flatten())
    SER_Write(hexstream)

    # 大约每1秒刷新一次
    wait_time += 1 - seconds_elapsed
    if wait_time > 0:
        time.sleep(wait_time)
    # 测试用：显示帧率
    # print(1 / seconds_elapsed)


# 独立线程加载，忽略错误，以免错误影响到程序的其他功能
def load_hardware_monitor():
    from HardwareMonitor import Hardware
    from HardwareMonitor.Util import SensorValueToString

    class UpdateVisitor(Hardware.IVisitor):
        __namespace__ = "TestHardwareMonitor"

        def __init__(self):
            self.sensors = []

        def VisitComputer(self, computer: Hardware.IComputer):
            computer.Traverse(self)

        def VisitHardware(self, hardware: Hardware.IHardware):
            hardware.Update()
            for subHardware in hardware.SubHardware:
                subHardware.Update()
                for sensor in subHardware.Sensors:
                    self.sensors.append([subHardware, sensor])

            for sensor in hardware.Sensors:
                self.sensors.append([hardware, sensor])

        def VisitParameter(self, parameter: Hardware.IParameter):
            pass

        def VisitSensor(self, sensor: Hardware.ISensor):
            pass

    def format_sensor_name(hardware, sensor):
        return "%s: %s - %s" % (hardware.Name, str(sensor.SensorType), sensor.Name)

    class HardwareMonitorManager:
        def __init__(self):
            self.computer = Hardware.Computer()
            self.computer.IsMotherboardEnabled = True
            self.computer.IsControllerEnabled = True
            self.computer.IsCpuEnabled = True
            self.computer.IsGpuEnabled = True
            self.computer.IsBatteryEnabled = True
            self.computer.IsMemoryEnabled = True
            self.computer.IsNetworkEnabled = True
            self.computer.IsStorageEnabled = True
            self.computer.Open()

            self.visitor = UpdateVisitor()
            self.computer.Accept(self.visitor)

            self.sensors = {format_sensor_name(hardware, sensor): (hardware, sensor) for hardware, sensor in
                            self.visitor.sensors}

        def get_value(self, sensor_name):
            hardware, sensor = self.sensors[sensor_name]
            hardware.Update()
            return sensor.Value

        def get_value_formatted(self, sensor_name):
            hardware, sensor = self.sensors[sensor_name]
            hardware.Update()
            return sensor.Value, SensorValueToString(sensor.Value, sensor.SensorType)

    return HardwareMonitorManager


custom_selected_names = [""] * 2
custom_selected_displayname = [""] * 2
custom_selected_names_tech = [""] * 6

custom_last_refresh_time = None
custom_plot_data = None


def show_custom_two_rows(text_color=(255, 128, 0)):
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global custom_last_refresh_time, custom_plot_data, State_change, wait_time, current_time
    global hardware_monitor_manager, custom_selected_names, custom_selected_displayname

    if hardware_monitor_manager is None:
        time.sleep(0.2)
        return

    bar_width = 2  # 每个点宽度
    image_height = 20  # 高度

    if State_change == 1:
        if custom_plot_data is None:
            custom_plot_data = [{"sent": 0, "recv": 0}] * (size_USE_X1 // bar_width)
        State_change = 0
        wait_time = 0
        custom_last_refresh_time = current_time
        # 初始化的时候，先显示0
        LCD_ADD(0, 0, size_USE_X1, size_USE_Y1)

    # 获取 libre hardware monitor 数值
    sent = None
    sent_text = None
    try:
        sent, sent_text = hardware_monitor_manager.get_value_formatted(custom_selected_names[0])
    except KeyError:
        pass
    if sent is None:
        sent = 0
        sent_text = "--"

    recv = None
    recv_text = None
    try:
        recv, recv_text = hardware_monitor_manager.get_value_formatted(custom_selected_names[1])
    except KeyError:
        pass
    if recv is None:
        recv = 0
        recv_text = "--"

    seconds_elapsed = (current_time - custom_last_refresh_time) / timedelta(seconds=1)
    custom_plot_data = custom_plot_data[1:] + [{"sent": sent, "recv": recv}]

    custom_last_refresh_time = current_time

    # 绘制图片

    im1 = Image.new("RGB", (size_USE_X1, size_USE_Y1), (0, 0, 0))

    draw = ImageDraw.Draw(im1)

    # 绘制文字

    # default_font字体支持中文
    draw.text((0, 0), custom_selected_displayname[0][0:5], fill=text_color, font=netspeed_font)
    text = "%s" % sent_text
    draw.text((80, 0), text, fill=text_color, font=netspeed_font)
    draw.text((0, 40), custom_selected_displayname[1][0:5], fill=text_color, font=netspeed_font)
    text = "%s" % recv_text
    draw.text((80, 40), text, fill=text_color, font=netspeed_font)

    # 绘图
    # 决定最小范围
    min_max = [0.01, 0.01]
    # 百分比或温度的，是100
    if sent_text[-1] in ("%", "C"):
        min_max[0] = 100
    if recv_text[-1] in ("%", "C"):
        min_max[1] = 100

    for start_y, key, color, minmax_it in zip([19, 59], ["sent", "recv"], [(235, 139, 139), (146, 211, 217)], min_max):
        sent_values = [data[key] for data in custom_plot_data]

        max_value = max(minmax_it, max(sent_values))

        for i, sent in enumerate(sent_values[-80:]):
            # Scale the sent value to the image height
            bar_height = int(sent * image_height / max_value) if max_value else 0
            x0 = i * bar_width
            y0 = image_height - bar_height + start_y
            x1 = (i + 1) * bar_width - 1
            y1 = image_height + start_y - 1

            # Draw the Green bar
            draw.rectangle([x0, y0, x1, max(y0, y1)], fill=color)

    rgb888 = np.asarray(im1)

    rgb565 = rgb888_to_rgb565(rgb888)
    # arr = np.frombuffer(rgb565.flatten().tobytes(), dtype=np.uint16).astype(np.uint32)
    hexstream = Screen_Date_Process(rgb565.flatten())
    SER_Write(hexstream)

    # 大约每1秒刷新一次
    wait_time += 1 - seconds_elapsed
    if wait_time > 0:
        time.sleep(wait_time)
    # 测试用：显示帧率
    # print(1 / seconds_elapsed)


mini_mark_parser = MiniMarkParser()

full_custom_template = "p Hello world"
full_custom_error = "OK"


def get_full_custom_im():
    global full_custom_template, full_custom_error, mini_mark_parser
    global hardware_monitor_manager, custom_selected_names_tech

    full_custom_error_tmp = ""
    # 获取 libre hardware monitor 数值
    custom_values = []
    for name in custom_selected_names_tech:
        value = None
        value_formatted = "--"
        if name != "":
            try:
                value, value_formatted = hardware_monitor_manager.get_value_formatted(name)
                if value is None:
                    full_custom_error_tmp += "获取项目 \"%s\" 失败，请尝试以管理员身份运行本程序" % name
            except KeyError:
                pass
        custom_values.append((value, value_formatted))

    # 绘制图片

    im1 = Image.new("RGB", (size_USE_X1, size_USE_Y1), (255, 255, 255))

    draw = ImageDraw.Draw(im1)
    error_line = ""
    record_dict = {str(i + 1): v for i, (_, v) in enumerate(custom_values)}
    record_dict_value = {str(i + 1): v for i, (v, _) in enumerate(custom_values)}
    try:
        mini_mark_parser.reset_state()
        for line in full_custom_template.split('\n'):
            line = line.rstrip('\r').strip()  # possible
            if line == "":
                continue
            error_line = line
            mini_mark_parser.parse_line(line, draw, im1, record_dict=record_dict, record_dict_value=record_dict_value)
        if full_custom_error_tmp != "":
            if full_custom_error_tmp != full_custom_error:
                full_custom_error = full_custom_error_tmp
        elif full_custom_error != "OK":
            full_custom_error = "OK"
    except Exception as e:
        full_custom_error = "%s\nerror line: %s" % (traceback.format_exc(), error_line)
        im1.paste((255, 0, 255), (0, 0, im1.size[0], im1.size[1]))

    return im1


def show_full_custom(text_color=(255, 128, 0)):
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global custom_last_refresh_time, State_change, wait_time, hardware_monitor_manager, current_time

    if hardware_monitor_manager is None:
        time.sleep(0.2)
        return

    if State_change == 1:
        # 初始化
        State_change = 0
        wait_time = 0
        custom_last_refresh_time = current_time
        LCD_ADD(0, 0, size_USE_X1, size_USE_Y1)

    seconds_elapsed = (current_time - custom_last_refresh_time) / timedelta(seconds=1)

    custom_last_refresh_time = current_time

    im1 = get_full_custom_im()

    rgb888 = np.asarray(im1)

    rgb565 = rgb888_to_rgb565(rgb888)
    # arr = np.frombuffer(rgb565.flatten().tobytes(), dtype=np.uint16).astype(np.uint32)
    hexstream = Screen_Date_Process(rgb565.flatten())
    SER_Write(hexstream)

    # 大约每1秒刷新一次
    wait_time += 1 - seconds_elapsed
    if wait_time > 0:
        time.sleep(wait_time)


netspeed_font_size = 20
default_font = MiniMark.load_font("simhei.ttf", netspeed_font_size)
netspeed_font = MiniMark.load_font("resource/Orbitron-Bold.ttf", netspeed_font_size - 4)


def save_config(config_obj):
    with open("MSU2_MINI.json", "w", encoding="utf-8") as f:
        json.dump(config_obj, f)


def load_config():
    try:
        with open("MSU2_MINI.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def UI_Page():  # 进行图像界面显示
    global Text1
    global machine_model, State_change, LCD_Change_use, Label1, Label3, Label4, Label5, Label6
    global custom_selected_names, custom_selected_displayname, custom_selected_names_tech, full_custom_template

    config_obj = load_config()
    machine_model = config_obj.get("state_machine", 3901)
    LCD_Change_use = config_obj.get("lcd_change", 0)

    # 创建主窗口
    window = tk.Tk()  # 实例化主窗口
    window.title("MG USB屏幕助手V1.0")  # 设置标题
    # 创建 Frame 容器，并将其填充到整个窗口
    root = tk.Frame(window, bg="white smoke", padx=10, pady=10, highlightthickness=1, highlightcolor="lightgray")
    root.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # 设备连接状态标签
    Label1 = tk.Label(root, text="设备未连接", fg="white", bg="red")
    Label1.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

    # 隐藏按钮

    def quit_window(icon, item):
        icon.stop()
        window.destroy()

    def show_window(icon, item):
        global Device_State, Device_State_Labelen
        icon.stop()
        window.deiconify()  # 恢复窗口

        if Device_State_Labelen == 1:
            Device_State_Labelen = 0
        elif Device_State_Labelen == 3:
            Device_State_Labelen = 2
            set_device_state(Device_State)

    def hide_to_tray(event=None):
        global Device_State_Labelen
        try:
            image = Image.open(MiniMark.get_resource("resource/icon.ico"))
        except Exception:
            # 没找到图标时使用一个灰方块做图标
            image = Image.new("RGB", (16, 16), (128, 128, 128))
        try:
            window.withdraw()  # 隐藏窗口
            menu = (
                pystray.MenuItem("显示", show_window, default=True),
                pystray.MenuItem("退出", quit_window)
            )
            icon = pystray.Icon("MG", image, "MSU2_mini", menu)

            Device_State_Labelen = 1

            icon.run()  # 等待恢复窗口
        except Exception as e:
            print("failed to use pystray to hide to tray, %s" % traceback.format_exc())
            window.deiconify()  # 恢复窗口

    hide_btn = ttk.Button(root, text="隐藏", width=12, command=hide_to_tray)
    hide_btn.grid(row=0, column=1, padx=5, pady=5)
    hide_btn.focus_set()  # 设置默认焦点

    # 选择和烧写按钮

    Label3 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label3.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    btn3 = ttk.Button(root, text="选择背景图像", width=12, command=Get_Photo_Path1)
    btn3.grid(row=1, column=1, padx=5, pady=5)
    btn5 = ttk.Button(root, text="烧写", width=8, command=Write_Photo_Path1)
    btn5.grid(row=1, column=2, padx=5, pady=5)

    Label4 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label4.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
    btn4 = ttk.Button(root, text="选择闪存固件", width=12, command=Get_Photo_Path2)
    btn4.grid(row=2, column=1, padx=5, pady=5)
    btn6 = ttk.Button(root, text="烧写", width=8, command=Write_Photo_Path2)
    btn6.grid(row=2, column=2, padx=5, pady=5)

    Label5 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label5.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    btn10 = ttk.Button(root, text="选择相册图像", width=12, command=Get_Photo_Path3)
    btn10.grid(row=3, column=1, padx=5, pady=5)
    btn8 = ttk.Button(root, text="烧写", width=8, command=Write_Photo_Path3)
    btn8.grid(row=3, column=2, padx=5, pady=5)

    Label6 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label6.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
    btn11 = ttk.Button(root, text="选择动图文件", width=12, command=Get_Photo_Path4)
    btn11.grid(row=4, column=1, padx=5, pady=5)
    btn9 = ttk.Button(root, text="烧写", width=8, command=Write_Photo_Path4)
    btn9.grid(row=4, column=2, padx=5, pady=5)

    # 创建颜色滑块

    def update_label_color():
        global color_use, rgb_tuple, State_change
        r1 = int(text_color_red_scale.get())
        g1 = int(text_color_green_scale.get())
        b1 = int(text_color_blue_scale.get())
        color_use = (r1 << 11) | (g1 << 5) | b1  # 彩色图片点阵算法 5R6G5B
        r2 = r1 * 255 // 31
        g2 = g1 * 255 // 63
        b2 = b1 * 255 // 31
        rgb_tuple = (r2, g2, b2)  # rgb
        if Label2:
            color_La = "#{:02x}{:02x}{:02x}".format(r2, g2, b2)
            Label2.config(bg=color_La)
        State_change = 1

    def update_label_color_red():
        global color_use
        r1 = int(text_color_red_scale.get())
        if (color_use >> 11) != r1:
            update_label_color()

    def update_label_color_green():
        global color_use
        g1 = int(text_color_green_scale.get())
        if ((color_use & 2047) >> 5) != g1:
            update_label_color()

    def update_label_color_blue():
        global color_use
        b1 = int(text_color_blue_scale.get())
        if (color_use & 31) != b1:
            update_label_color()

    scale_desc = tk.Label(root, text="文字颜色")
    scale_desc.grid(row=0, column=3, columnspan=2, sticky=tk.W, padx=5, pady=5)

    text_color_red_scale = ttk.Scale(root, from_=0, to=31, orient=tk.HORIZONTAL)
    text_color_red_scale.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
    text_color_red_scale.set(config_obj.get("text_color_r", 31))
    text_color_red_scale.config(command=lambda x: update_label_color_red())

    scale_ind_r = tk.Label(root, bg="red", width=2)
    scale_ind_r.grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)

    text_color_green_scale = ttk.Scale(root, from_=0, to=63, orient=tk.HORIZONTAL)
    text_color_green_scale.grid(row=2, column=3, sticky=tk.W, padx=5, pady=5)
    text_color_green_scale.set(config_obj.get("text_color_g", 32))
    text_color_green_scale.config(command=lambda x: update_label_color_green())

    scale_ind_g = tk.Label(root, bg="green", width=2)
    scale_ind_g.grid(row=2, column=4, padx=5, pady=5, sticky=tk.W)

    text_color_blue_scale = ttk.Scale(root, from_=0, to=31, orient=tk.HORIZONTAL)
    text_color_blue_scale.grid(row=3, column=3, sticky=tk.W, padx=5, pady=5)
    text_color_blue_scale.set(config_obj.get("text_color_b", 0))
    text_color_blue_scale.config(command=lambda x: update_label_color_blue())

    scale_ind_b = tk.Label(root, bg="blue", width=2)
    scale_ind_b.grid(row=3, column=4, padx=5, pady=5, sticky=tk.W)

    Label2 = tk.Label(root, width=2)  # 颜色预览框
    Label2.grid(row=4, column=3, columnspan=2, padx=5, pady=5)
    update_label_color()

    # 自定义显示内容

    custom_selected_names = config_obj.get("custom_selected_names", custom_selected_names)
    custom_selected_displayname = config_obj.get("custom_selected_displayname", custom_selected_displayname)
    custom_selected_names_tech = config_obj.get("custom_selected_names_tech", custom_selected_names_tech)
    full_custom_template = config_obj.get("full_custom_template", full_custom_template)

    def center_window(top_window):
        # Get the dimensions of the screen
        screen_width = top_window.winfo_screenwidth()
        screen_height = top_window.winfo_screenheight()

        # Get the dimensions of the parent window
        parent_width = window.winfo_width()
        parent_height = window.winfo_height()
        parent_x = window.winfo_x()
        parent_y = window.winfo_y()

        # Get the dimensions of the child window (default size)
        top_window.update_idletasks()  # Update the window's size information
        child_width = top_window.winfo_width()
        child_height = top_window.winfo_height()

        # Calculate the position
        x = parent_x + (parent_width - child_width) // 2
        y = parent_y + (parent_height - child_height) // 2

        # Check if the child window exceeds the right boundary of the screen
        x1 = screen_width - child_width - 50
        if x > x1:
            x = x1

        # Check if the child window exceeds the bottom boundary of the screen
        y1 = screen_height - child_height - 50
        if y > y1:
            y = y1

        # Ensure the child window is not positioned outside of the left or top borders of the screen
        if x < 50:
            x = 50

        if y < 50:
            y = 50

        # Set the position of the child window
        top_window.geometry("+%d+%d" % (x, y))

    def show_custom():
        global full_custom_template, sub_window, custom_selected_names_tech
        if hardware_monitor_manager is None:
            tk.messagebox.showerror(message="Libre Hardware Monitor 正在加载，请稍候……")
            return

        if sub_window is not None:
            sub_window.deiconify()  # 如果已经创建过子窗口直接显示
            window.attributes("-disabled", True)  # 禁用主窗口
            return

        sub_window = tk.Toplevel(window)  # 创建一个子窗口
        sub_window.title("自定义显示内容")
        sub_window.transient(window)  # 置于主窗口前面
        sub_window.resizable(0, 0)  # 锁定窗口大小不能改变

        def on_closing():
            window.attributes("-disabled", False)  # 启用主窗口
            # 点击关闭时仅隐藏子窗口，不真正关闭
            sub_window.withdraw()

        sub_window.protocol("WM_DELETE_WINDOW", on_closing)
        window.attributes("-disabled", True)  # 禁用主窗口

        sensor_vars = []
        sensor_displayname_vars = []
        sensor_vars_tech = []

        # 创建一个选项卡
        notebook = tkinter.ttk.Notebook(sub_window)
        notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W)

        # 添加“自定义多项”标签页

        tech_frame = tkinter.Frame(master=sub_window)
        notebook.add(tech_frame, text="  显示多项数值  ")
        tech_frame.focus_set()  # 设置默认焦点

        desc_label = tk.Label(tech_frame, text="名称")
        desc_label.grid(row=1, column=0, padx=5, pady=5)
        desc_label = tk.Label(tech_frame, text="项目")
        desc_label.grid(row=1, column=1, padx=5, pady=5)

        def update_sensor_value_tech(i):
            if custom_selected_names_tech[i] != sensor_vars_tech[i].get():
                custom_selected_names_tech[i] = sensor_vars_tech[i].get()
                get_full_custom_im()

        type_list = ["1. CPU", "2. GPU", "3. 内存"]
        row = 6  # 设置自定义项目数
        for row1 in range(row):
            if row1 >= len(custom_selected_names_tech):
                custom_selected_names_tech = custom_selected_names_tech + [""]
            if row1 < len(type_list):
                rowtype = type_list[row1]
            else:
                rowtype = "%d." % (row1 + 1)

            sensor_label = tk.Label(tech_frame, text=rowtype, width=8, anchor=tk.W)
            sensor_label.grid(row=row1 + 2, column=0, sticky=tk.EW, padx=5, pady=5)

            sensor_var = tk.StringVar(tech_frame, "")
            sensor_vars_tech.append(sensor_var)
            sensor_combobox = ttk.Combobox(tech_frame, textvariable=sensor_var,
                                           values=[""] + list(hardware_monitor_manager.sensors.keys()), width=60)
            sensor_combobox.set(custom_selected_names_tech[row1])
            sensor_combobox.bind("<<ComboboxSelected>>", lambda event, ii=row1: update_sensor_value_tech(ii))
            sensor_combobox.grid(row=row1 + 2, column=1, sticky=tk.EW, padx=5, pady=5)
            sensor_combobox.configure(state="readonly")  # 设置选择框不可编辑，这样会导致无法查看全部的选择文字

        row += 2
        desc_label = tk.Label(tech_frame, text="完全自定义模板代码：", anchor=tk.W, justify=tk.LEFT)
        desc_label.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # 创建自定义内容输入框
        row += 1
        text_frame = ttk.Frame(tech_frame, padding="5")
        text_frame.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        def update_global_text(event=None):
            global full_custom_template
            # Get the current content of the text area and update the global variable
            full_custom_template_tmp = text_area.get("1.0", tk.END).rstrip('\n')  # tk.END会多一个换行
            if event is None or full_custom_template != full_custom_template_tmp:
                full_custom_template = full_custom_template_tmp
                im = get_full_custom_im()
                tk_im = ImageTk.PhotoImage(im)
                canvas.create_image(0, 0, anchor=tk.NW, image=tk_im)
                canvas.image = tk_im

        text_area = tk.Text(text_frame, wrap=tk.WORD, width=40, height=10, padx=5, pady=5)
        text_area.insert(tk.END, full_custom_template)
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        view_frame = ttk.Frame(text_frame, padding="10")
        view_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=0, pady=0)

        desc_label = tk.Label(view_frame, text="效果预览：", anchor=tk.NW, justify=tk.LEFT, padx=5, pady=5)
        desc_label.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

        canvas = tk.Canvas(view_frame, width=160, height=80)
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        text_area.bind("<KeyRelease>", update_global_text)
        update_global_text(None)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area["yscrollcommand"] = scrollbar.set

        row += 1
        btn_frame = ttk.Frame(tech_frame, padding="5")
        btn_frame.grid(row=row, column=0, columnspan=2, padx=0, pady=0, sticky=tk.W)

        def show_error():
            print(full_custom_error)
            tk.messagebox.showinfo(message=full_custom_error, parent=sub_window)

        show_error_btn = ttk.Button(btn_frame, text="查看模板错误", width=15, command=show_error)
        show_error_btn.grid(row=0, column=0, padx=5, pady=5)

        def example(i):
            global full_custom_template
            if i == 1:
                full_custom_template = '\n'.join(
                    ["i resource/example_background.png", "c #ff3333", "f resource/Orbitron-Regular.ttf 22",
                     "m 16 16", "v 1 {:.0f}", "p %",
                     "m 96 16", "v 2 {:.0f}", "p %",
                     "m 96 44", "v 3 {:.0f}", "p %"])
            elif i == 2:
                full_custom_template = '\n'.join(
                    ["m 8 8", "f resource/Orbitron-Bold.ttf 20", "p CPU", "t 8 0", "c #3366cc", "v 1",
                     "m 8 28", "c #000000", "f resource/Orbitron-Bold.ttf 20", "p GPU", "t 8 0", "c #3366cc", "v 2",
                     "m 8 48", "c #000000", "f resource/Orbitron-Bold.ttf 20", "p RAM", "t 8 0", "c #3366cc", "v 3"])
            text_area.delete("1.0", tk.END)
            text_area.insert(tk.END, full_custom_template)
            update_global_text(None)

        example_btn_1 = ttk.Button(btn_frame, text="科技", width=15, command=lambda: example(1))
        example_btn_1.grid(row=0, column=1, padx=5, pady=5)
        example_btn_2 = ttk.Button(btn_frame, text="简单", width=15, command=lambda: example(2))
        example_btn_2.grid(row=0, column=2, padx=5, pady=5)

        def show_instruction():
            instruction = '\n'.join(
                [
                    "自定义显示内容。一共有两个模式，第一个固定显示两行，有图表；第二个是完全自定义模式，可以自己加文本和图片。",
                    "模板代码在框中输入，结果可以在预览中看到，模板代码从前往后顺序执行，每行执行一个操作。",
                    "p <文本>   \t绘制文本，会自动移动坐标",
                    "a <锚点>   \t更改文本锚点，参考Pillow文档，如la,ra,ls,rs",
                    "m <x> <y>  \t移动到坐标(x,y)",
                    "t <x> <y>  \t相对当前位置移动(x,y)",
                    "f <文件名> <字号> \t更换字体，文件名如 arial.ttf",
                    "c <hex码>  \t更改文字颜色，如 c #ffff00",
                    "i <文件名> \t绘制图片",
                    "v <序号> <格式> \t绘制选择项目的值，格式符可省略，如 v 1 {:.2f}",
                    "\n* 部分项目需要以管理员身份运行本程序，否则可能显示为<*>或--，甚至可能不会在项目下拉列表中显示。"
                ]
            )

            tk.messagebox.showinfo(message=instruction, parent=sub_window)

        show_instruction_btn = ttk.Button(btn_frame, text="说明", width=15, command=show_instruction)
        show_instruction_btn.grid(row=0, column=3, padx=5, pady=5)

        # 添加“简单两项图表”标签页

        simple_frame = tkinter.Frame(master=sub_window)
        notebook.add(simple_frame, text="  显示两项图表  ")

        desc_label = tk.Label(simple_frame, text="名称")
        desc_label.grid(row=1, column=0, padx=5, pady=5)
        desc_label = tk.Label(simple_frame, text="项目")
        desc_label.grid(row=1, column=1, padx=5, pady=5)

        def update_sensor_value(i):
            global custom_plot_data
            if custom_selected_names[i] != sensor_vars[i].get():
                custom_selected_names[i] = sensor_vars[i].get()

                # 项目变更时清空旧项目数据
                if custom_plot_data is None:
                    return
                key = None
                if i == 0:
                    key = "sent"
                elif i == 1:
                    key = "recv"
                for index in range(0, len(custom_plot_data)):
                    custom_plot_data[index][key] = 0

        def change_sensor_displayname(i):
            if custom_selected_displayname[i] != sensor_displayname_vars[i].get():
                custom_selected_displayname[i] = sensor_displayname_vars[i].get()

        # "简单"模式显示2项
        for row in range(2):
            sensor_displayname_var = tk.StringVar(simple_frame, "")
            sensor_displayname_vars.append(sensor_displayname_var)
            sensor_displayname_var.set(custom_selected_displayname[row])
            sensor_entry = ttk.Entry(simple_frame, textvariable=sensor_displayname_var, width=8)
            sensor_entry.bind("<KeyRelease>", lambda event, ii=row: change_sensor_displayname(ii))
            sensor_entry.grid(row=row + 2, column=0, sticky=tk.EW, padx=5, pady=5)

            sensor_var = tk.StringVar(simple_frame, "")
            sensor_vars.append(sensor_var)
            sensor_combobox = ttk.Combobox(simple_frame, textvariable=sensor_var,
                                           values=[""] + list(hardware_monitor_manager.sensors.keys()), width=60)
            sensor_combobox.set(custom_selected_names[row])
            sensor_combobox.bind("<<ComboboxSelected>>", lambda event, ii=row: update_sensor_value(ii))
            sensor_combobox.grid(row=row + 2, column=1, sticky=tk.EW, padx=5, pady=5)
            sensor_combobox.configure(state="readonly")  # 设置选择框不可编辑，这样会导致无法查看全部的选择文字

        center_window(sub_window)

    show_custom_btn = ttk.Button(root, text="自定义内容", width=12, command=show_custom)
    show_custom_btn.grid(row=5, column=1, padx=5, pady=5)

    # 方向和翻页按钮

    btn7 = ttk.Button(root, text="切换显示方向", width=12, command=LCD_Change)
    btn7.grid(row=6, column=1, padx=5, pady=5)

    btn1 = ttk.Button(root, text="上翻页", width=8, command=Page_UP)
    btn1.grid(row=5, column=2, padx=5, pady=5)

    btn2 = ttk.Button(root, text="下翻页", width=8, command=Page_Down)
    btn2.grid(row=6, column=2, padx=5, pady=5)

    # 屏幕编号

    number_var = tk.StringVar(root, "1")

    def change_screenshot_monitor(*args):
        global screenshot_monitor_id, screenshot_region, cropped_monitor
        try:
            screenshot_monitor_id_tmp = int(number_var.get())
        except ValueError as e:
            if len(number_var.get()) > 0:
                print("Invalid number entered: %s" % traceback.format_exc())
            return
        if screenshot_monitor_id == screenshot_monitor_id_tmp:
            return

        with mss() as sct:
            if 0 < screenshot_monitor_id_tmp <= len(sct.monitors[1:]):
                screenshot_monitor_id = screenshot_monitor_id_tmp
                try:
                    monitor = sct.monitors[screenshot_monitor_id]
                except IndexError:
                    monitor = sct.monitors[1]
                cropped_monitor = {
                    "left": (screenshot_region[0] or 0) + monitor["left"],
                    "top": (screenshot_region[1] or 0) + monitor["top"],
                    "width": screenshot_region[2] or monitor["width"],
                    "height": screenshot_region[3] or monitor["height"],
                    "mon": screenshot_monitor_id,
                }
                State_change = 1  # 刷新屏幕

    number_var.trace_add("write", change_screenshot_monitor)
    number_var.set(config_obj.get("number_var", "1"))

    label_screen_number = ttk.Label(root, text="屏幕编号")
    label_screen_number.grid(row=5, column=3, padx=5, pady=5)

    number_entry = ttk.Entry(root, textvariable=number_var, width=4)
    number_entry.grid(row=5, column=4, sticky=tk.EW, padx=5, pady=5)

    # fps

    fps_var = tk.StringVar(root, "100")

    def change_fps(*args):
        global screenshot_limit_fps
        screenshot_limit_fps_tmp = 0
        try:
            screenshot_limit_fps_tmp = int(fps_var.get())
        except ValueError as e:
            if len(fps_var.get()) > 0:
                print("Invalid number entered: %s" % traceback.format_exc())
        if 0 < screenshot_limit_fps_tmp != screenshot_limit_fps:
            screenshot_limit_fps = screenshot_limit_fps_tmp

    fps_var.trace_add("write", change_fps)
    fps_var.set(config_obj.get("fps_var", "100"))

    label = ttk.Label(root, text="最大 FPS")
    label.grid(row=6, column=3, padx=5, pady=5)

    fps_entry = ttk.Entry(root, textvariable=fps_var, width=4)
    fps_entry.grid(row=6, column=4, sticky=tk.EW, padx=5, pady=5)

    # 区域

    screen_region_var = tk.StringVar(root, "0,0,,")

    def change_screen_region(*args):
        global screenshot_region, cropped_monitor, screenshot_monitor_id, State_change
        try:
            t = tuple((None if x.strip() == "" else int(x)) for x in screen_region_var.get().split(","))
        except ValueError as e:
            if len(screen_region_var.get()) > 0:
                print("screen_region Invalid: %s" % traceback.format_exc())
            return
        if len(t) != 4:
            print("screen_region Invalid, example: 0,0,160,80")
            return
        if screenshot_region == t:
            return

        screenshot_region = t
        with mss() as sct:
            try:
                monitor = sct.monitors[screenshot_monitor_id]
            except IndexError:
                monitor = sct.monitors[1]
        cropped_monitor = {
            "left": (screenshot_region[0] or 0) + monitor["left"],
            "top": (screenshot_region[1] or 0) + monitor["top"],
            "width": screenshot_region[2] or monitor["width"],
            "height": screenshot_region[3] or monitor["height"],
            "mon": screenshot_monitor_id,
        }
        State_change = 1  # 刷新屏幕

    screen_region_var.trace_add("write", change_screen_region)
    screen_region_var.set(config_obj.get("screen_region_var", "0,0,,"))

    label = ttk.Label(root, text="投屏区域(左,上,宽,高):")
    label.grid(row=7, column=1, columnspan=2, sticky=tk.E, padx=5, pady=5)

    screen_region_entry = ttk.Entry(root, textvariable=screen_region_var, width=11)
    screen_region_entry.grid(row=7, column=3, columnspan=2, sticky=tk.EW, padx=5, pady=5)

    # 创建信息显示文本框
    Text1 = tk.Text(root, state=tk.DISABLED, width=22, height=4, padx=5, pady=5)
    Text1.grid(row=5, column=0, rowspan=3, columnspan=1, sticky=tk.NS, padx=5, pady=5)

    def on_closing():
        # 结束时保存配置
        config_obj = {
            "text_color_r": int(text_color_red_scale.get()),
            "text_color_g": int(text_color_green_scale.get()),
            "text_color_b": int(text_color_blue_scale.get()),
            "state_machine": machine_model,
            "lcd_change": LCD_Change_use,
            "number_var": screenshot_monitor_id,
            "fps_var": screenshot_limit_fps,
            "screen_region_var": screen_region_var.get(),
            "custom_selected_names": custom_selected_names,
            "custom_selected_displayname": custom_selected_displayname,
            "custom_selected_names_tech": custom_selected_names_tech,
            "full_custom_template": full_custom_template,
        }
        save_config(config_obj)

        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.resizable(0, 0)  # 锁定窗口大小不能改变
    # 点击最小化按钮时隐藏窗口
    window.bind("<Unmap>", lambda event: hide_to_tray() if window.state() == "iconic" else False)
    if len(sys.argv) >= 2 and sys.argv[1] == "hide":
        hide_to_tray()  # 命令行启动时设置隐藏

    # 参数全部获取后再启动截图线程
    screen_shot_thread.start()
    screen_process_thread.start()

    # 进入消息循环
    window.mainloop()


class MSN_Device:
    def __init__(self, com, version):
        self.com = com  # 登记串口位置
        self.version = version  # 登记MSN版本
        self.name = "MSN"  # 登记设备名称
        # self.baud_rate = 19200  # 登记波特率（没有用到）


class MSN_Data:
    def __init__(self, name, unit, family, data):
        self.name = name
        self.unit = unit
        self.family = family
        self.data = data


# Device_State_Labelen: 0无修改，1窗口已隐藏，2窗口已恢复有修改，3窗口已隐藏有修改
def set_device_state(state):
    global Label1, Device_State, Device_State_Labelen
    if Device_State != state:
        Device_State = state
    if Device_State_Labelen == 2:
        Device_State_Labelen = 0
    if Device_State_Labelen == 0:
        while not hasattr(Label1, "config"):  # 页面未加载完
            time.sleep(0.1)
        if Device_State == 1:
            Label1.config(text="设备已连接", fg="white", bg="green")
        else:
            Label1.config(text="设备未连接", fg="white", bg="red")
    elif Device_State_Labelen == 1:
        Device_State_Labelen = 3


def Get_MSN_Device(port_list):  # 尝试获取MSN设备
    global ADC_det, ser, State_change, current_time
    global Screen_Error, LCD_Change_now, LCD_Change_use
    if ser is not None and ser.is_open:
        ser.close()  # 先将异常的串口连接关闭，防止无法打开

    # 对串口进行监听，确保其为MSN设备
    My_MSN_Device = None
    for i in range(0, len(port_list)):
        try:  # 尝试打开串口
            # 初始化串口连接,初始使用
            ser = serial.Serial(port_list[i].name, 115200, timeout=5.0,
                                write_timeout=5.0, inter_byte_timeout=0.1)
        except Exception as e:  # 出现异常
            print("%s 无法打开,请检查是否被其他程序占用: %s" % (port_list[i].name, e))
            if ser is not None and ser.is_open:
                ser.close()  # 将串口关闭，防止下次无法打开
            time.sleep(0.1)  # 防止频繁重试
            continue  # 尝试下一个端口
        recv = SER_Read()
        if recv == 0:
            print("未接收到设备响应，打开失败：%s" % port_list[i].name)
            ser.close()  # 将串口关闭，防止下次无法打开
            continue  # 尝试下一个端口
        else:
            recv = recv.decode("gbk")  # 获取串口数据

        # 逐字解析编码，收到6个字符以上数据时才进行解析
        for n in range(0, len(recv) - 5):
            # 当前字节为0时进行解析，确保为MSN设备，确保版本号为数字ASC码
            if not (ord(recv[n]) == 0 and recv[n + 1: n + 4] == "MSN"
                    and "0" <= recv[n + 4] <= "9" and "0" <= recv[n + 5] <= "9"):
                continue
            msn_version = (ord(recv[n + 4]) - 48) * 10 + (ord(recv[n + 5]) - 48)
            # 可以逐个加入数组
            hex_code = int(0).to_bytes(1, byteorder="little")
            hex_code = hex_code + b"MSNCN"
            SER_Write(hex_code)  # 返回消息
            recv = SER_Read()
            if recv == 0:
                print("连接失败，设备发送消息失败：%s" % port_list[i].name)
                break  # 未接收到响应，串口异常，直接退出
            else:
                recv = recv.decode("gbk")  # 获取串口数据
            # 确保为MSN设备
            if len(recv) > 5 and ord(recv[0]) == 0 and recv[1:6] == "MSNCN":
                print("%s MSN设备%s连接完成" % (get_formatted_time_string(current_time), port_list[i].name))
                # 对MSN设备进行登记
                My_MSN_Device = MSN_Device(port_list[i].name, msn_version)
                break  # 退出当前for循环
            else:
                print("MSN设备%s无法连接，请检查连接是否正常" % port_list[i].name)

        if My_MSN_Device is None:
            print("设备校验失败：%s" % port_list[i].name)
            ser.close()  # 将串口关闭，防止下次无法打开
        else:
            break  # 连接成功即退出循环

    if My_MSN_Device is None:  # 没有找到可用的设备
        return

    My_MSN_Data = Read_M_SFR_Data(256)  # 读取u8在0x0100之后的128字节
    Print_MSN_Data(My_MSN_Data)  # 解析字节中的数据格式
    # Read_MSN_Data(My_MSN_Data)  # 从设备读取更详细的数据，如序列号等
    LCD_Change_now = LCD_Change_use
    LCD_State(LCD_Change_now)  # 配置显示方向
    State_change = 1  # 状态发生变化
    Screen_Error = 0
    # 配置按键阈值
    ADC_det = (Read_ADC_CH(9) + Read_ADC_CH(9)) / 2
    ADC_det = ADC_det - 125  # 根据125的阈值判断是否被按下
    set_device_state(1)  # 可以正常连接

    # 闪存芯片P25D80具有1024KB的存储空间，以256B为一页，共4096页，使用0~4095作为页地址
    # 闪存上存储的数据信息如下：
    # for i in range(1, 37):  # 36张动图数据，160*80分辨率彩色图片，每张占用100个Page，共3600页
    #     Write_Flash_Photo_fast(100 * (i - 1), str(i))
    # Write_Flash_Photo_fast(3600, "Demo1")  # 240*240单色图片，占用29个Page
    # Write_Flash_Photo_fast(3629, "N48X66P")  # 48*66分辨率数码管图像，占用22个Page
    # Write_Flash_ZK(3651, "ASC64")  # 时钟字体，32*64分辨率ASCII表格，占用128个Page
    # Write_Flash_Photo_fast(3779, "logo")  # 240*102单色LOGO,占用12个Page
    # Write_Flash_Photo_fast(3791, "J1")  # 240*240单色图片，占用29个Page
    # Write_Flash_Photo_fast(3820, "MLOGO")  # 160*68单色图片，占用6个Page
    # Write_Flash_Photo_fast(3826, "CLK_BG")  # 时钟背景图像，160*80彩色图片，占用100个Page
    # Write_Flash_Photo_fast(3926, "PH1")  # 相册图像，160*80彩色图片，占用100个Page
    # Write_Flash_Photo_fast(4026, "N24X33P")  # 状态显示页面字体，24*33分辨率数码管图像，占用12个Page
    # Write_Flash_Photo_fast(4038, "MP1")  # 状态显示页面背景，160*80单色图片，占用7个Page


last_read_adc_time = current_time
read_adc_timedelta = timedelta(milliseconds=300)


def MSN_Device_1_State_machine():  # MSN设备1的循环状态机
    global machine_model, key_on, State_change, LCD_Change_now, LCD_Change_use, photo_path2
    global write_path_index, Img_data_use, color_use, rgb_tuple, last_read_adc_time, current_time

    if LCD_Change_now != LCD_Change_use:  # 显示方向与设置不符合
        LCD_Change_now = LCD_Change_use
        LCD_State(LCD_Change_now)  # 配置显示方向
        State_change = 1

    if write_path_index != 0:
        if write_path_index == 1:
            Write_Flash_hex_fast(3826, Img_data_use)
        elif write_path_index == 2:
            Write_Flash_Photo_fast(0, photo_path2)
        elif write_path_index == 3:
            Write_Flash_hex_fast(3926, Img_data_use)
        elif write_path_index == 4:
            Write_Flash_hex_fast(0, Img_data_use)
        write_path_index = 0
        State_change = 1

    # 加上or key_on == 1 用于增加释放按键的响应速度
    if current_time - last_read_adc_time > read_adc_timedelta or key_on == 1:
        last_read_adc_time = current_time
        # 检测按键是否被按下，兼具心跳功能
        if 0 < Read_ADC_CH(9) < ADC_det:
            if key_on == 0:
                key_on = 1
                Page_UP()
        elif key_on == 1:  # 按键不再按下
            key_on = 0

    if machine_model == 0:
        show_gif()
    elif machine_model == 1:
        show_PC_state(BLUE, BLACK)
    elif machine_model == 2:
        show_PC_state(color_use, BLACK)
    elif machine_model == 3:
        show_Photo1()
    elif machine_model == 4:
        show_PC_time()
    elif machine_model == 5:
        show_PC_Screen()
    elif machine_model == 3901:
        show_netspeed(text_color=rgb_tuple)
    elif machine_model == 3902:
        show_custom_two_rows(text_color=rgb_tuple)
    elif machine_model == 3903:
        show_full_custom(text_color=rgb_tuple)


def get_formatted_time_string(time):
    return time.strftime("%Y-%m-%d %H:%M:%S")


# print("该设备具有%d个内核和%d个逻辑处理器" % (psutil.cpu_count(logical=False), psutil.cpu_count()))
# print("该CPU主频为%.1fGHZ" % (psutil.cpu_freq().current / 1000))
# print("当前CPU占用率为%s%%" % psutil.cpu_percent())
# mem = psutil.virtual_memory()
# print("该设备具有%.0fGB的内存" % (mem.total / (1024 * 1024 * 1024)))
# print("当前内存占用率为%s%%" % mem.percent)
# battery = psutil.sensors_battery()
# if battery is not None:
#     print("电池剩余电量%d%%" % battery.percent)
# print("系统启动时间%s" % get_formatted_time_string(datetime.fromtimestamp(psutil.boot_time())))
# print("程序启动时间%s" % get_formatted_time_string(current_time))

key_on = 0
State_change = 1  # 状态发生变化
Screen_Error = 0
gif_num = 0
machine_model = 3901  # 定义初始状态
Device_State = 0  # 初始为未连接
Device_State_Labelen = 0  # 0无修改，1窗口已隐藏，2窗口已恢复有修改，3窗口已隐藏有修改
LCD_Change_use = 0  # 初始显示方向
LCD_Change_now = 0
color_use = RED  # 彩色图片点阵算法 5R6G5B
rgb_tuple = (0, 0, 0)  # RGB颜色
write_path_index = 0
photo_path1 = ""  # 背景图像路径
photo_path2 = ""  # 闪存固件路径
photo_path3 = ""  # 相册图像路径
photo_path4 = ""  # 动图文件路径

Label1 = None  # 设备状态显示框
Label3 = None  # 背景图像路径显示框
Label4 = None  # 闪存固件路径显示框
Label5 = None  # 相册图像路径显示框
Label6 = None  # 动图文件路径显示框
Text1 = None  # 信息显示文本框
ser = None  # 设备连接句柄
ADC_det = 0  # 按键阈值
sub_window = None  # 子窗口，设置为全局变量用于重新打开时不需要重复创建
hardware_monitor_manager = None


def load_task():
    global hardware_monitor_manager
    try:
        HardwareMonitorManager = load_hardware_monitor()
        hardware_monitor_manager = HardwareMonitorManager()
    except Exception as e:
        print("Libre hardware monitor 加载失败, %s" % traceback.format_exc())
    print("Libre hardware monitor load finished")


def daemon_task():
    global ser, current_time, Device_State, Device_State_Labelen

    while MG_daemon_running:
        try:
            current_time = datetime.now()
            if Device_State_Labelen == 2:
                set_device_state(Device_State)

            if Device_State == 1:  # 已检测到设备
                MSN_Device_1_State_machine()
            else:
                # 尝试获取MSN设备
                port_list = list(serial.tools.list_ports.comports())  # 查询所有串口
                # geezmo: 如果有 VID = 0x1a86 （沁恒）的，优先考虑这些设备，防止访问其他串口出错
                # 如果没有这些设备，或者 pyserial 没有提供信息，则不管
                wch_port_list = [x for x in port_list if x.vid == 0x1a86]
                Get_MSN_Device(wch_port_list)
                if Device_State == 0:
                    not_wch_port_list = [x for x in port_list if x.vid != 0x1a86]
                    Get_MSN_Device(not_wch_port_list)
                    if Device_State == 0:
                        print("%s 没有找到可用的MSN设备" % get_formatted_time_string(current_time))
                        time.sleep(1)  # 防止频繁重试
        except Exception as e:  # 出现非预期异常
            print("Exception in daemon_task, %s" % traceback.format_exc())
            time.sleep(1)  # 防止频繁重试

    # stop
    print("stop daemon")
    if ser is not None and ser.is_open:
        ser.close()  # 正常关闭串口


# 设备交互只能串行进行，所有的跟设备交互操作必须全部由daemon_thread完成
MG_daemon_running = True
MG_screen_thread_running = True
daemon_thread = threading.Thread(target=daemon_task)
screen_shot_thread = threading.Thread(target=screen_shot_task)
screen_process_thread = threading.Thread(target=screen_process_task)
load_thread = threading.Thread(target=load_task)

# tkinter requires the main thread
try:
    daemon_thread.start()  # 尽早启动daemon_thread
    load_thread.start()
    # 打开主页面
    UI_Page()
finally:
    # reap threads
    print("closing")

    MG_screen_thread_running = False
    MG_daemon_running = False
    if screen_shot_thread.is_alive():
        screen_shot_thread.join(timeout=5.0)
    if screen_process_thread.is_alive():
        screen_process_thread.join(timeout=5.0)
    if daemon_thread.is_alive():
        daemon_thread.join(timeout=5.0)
    if load_thread.is_alive():
        load_thread.join(timeout=5.0)
