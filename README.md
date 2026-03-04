# VeighNa框架的TdxQuant数据服务接口

<p align="center">
  <img src ="https://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-logo.png"/>
</p>

<p align="center">
    <img src ="https://img.shields.io/badge/version-1.0.0-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg" />
    <img src ="https://img.shields.io/github/license/vnpy/vnpy.svg?color=orange"/>
</p>

## 说明

基于TdxQuant开发，支持以下中国金融市场的K线数据：

* 股票：
  * SSE：上海证券交易所
  * SZSE：深圳证券交易所


## 安装

安装环境推荐基于4.0.0版本以上的【[**VeighNa Studio**](https://www.vnpy.com)】。

直接使用pip命令：

```
pip install vnpy_tdxquant
```


或者下载源代码后，解压后在cmd中运行：

```
pip install .
```


## 使用

在VeighNa中使用TdxQuant时，需要在全局配置中填写以下字段信息：

|名称|含义|必填|举例|
|---------|----|---|---|
|datafeed.name|名称|是|tdxquant|
|datafeed.username|用户名|是||通达信安装目录/PYPlugins/user|

使用过程中需要保持客户端运行，如果需要获取历史分钟K线，需要先通过客户端【盘后数据下载】功能下载K线（目前不支持盘中下载K线）。

如果通过客户端下载K线失败，可以尝试切换站点。
