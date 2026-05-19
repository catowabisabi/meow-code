#!/bin/bash
echo 'export ANDROID_HOME=$HOME/android-sdk' >> ~/.bashrc
echo 'export JAVA_HOME=$HOME/jdk-17' >> ~/.bashrc
echo 'export PATH=$HOME/flutter/bin:$PATH' >> ~/.bashrc
echo "Done. Last 5 lines of ~/.bashrc:"
tail -5 ~/.bashrc