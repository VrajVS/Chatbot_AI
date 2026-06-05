@echo off
title Ollama — CPU optimised (Intel UHD)

:: No discrete GPU — run on CPU only
set OLLAMA_NUM_GPU=0

:: Use all available CPU threads
set OLLAMA_NUM_THREAD=0

:: Allow requests from browser file:// pages (needed for the chatbot HTML)
set OLLAMA_ORIGINS=*

:: Keep one model loaded at a time to save RAM
set OLLAMA_NUM_PARALLEL=1

echo Starting Ollama (CPU mode — Intel UHD detected, no GPU offload available)
echo.
ollama serve
