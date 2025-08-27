#!/usr/bin/env python3
"""
Script de teste para verificar as modificações da API SVG Crop
Testa se as imagens são convertidas para PNG com canal alfa e fundo branco
"""

import requests
import zipfile
import io
from PIL import Image
import base64
import json
import sys

def test_svg_crop_api():
    """Testa a API com uma URL SVG de exemplo"""
    
    # URL da API local
    API_URL = "http://localhost:8877/crop_svg"
    
    # URL de exemplo de SVG (você pode substituir por uma URL real)
    test_svg_url = "https://fpd-exporter-staging-v2.s3.amazonaws.com/775cb0b423bf1151fd6b80065102535f264873c8-e41cfa57-f349-4239-82e7-f5179dba072e/uibr1017-0-combo-8_view_0.svg"
    
    print("=" * 60)
    print("TESTE DA API SVG CROP - Verificação PNG com Alfa e Fundo Branco")
    print("=" * 60)
    
    # Preparar requisição
    payload = {
        "svg_url": test_svg_url
    }
    
    print(f"\n📤 Enviando requisição para: {API_URL}")
    print(f"   SVG URL: {test_svg_url}")
    
    try:
        # Fazer requisição
        response = requests.post(API_URL, json=payload)
        
        if response.status_code == 200:
            print("✅ Resposta recebida com sucesso!")
            
            # Decodificar resposta JSON
            data = response.json()
            
            if data.get("success"):
                print(f"\n📊 Estatísticas do processamento:")
                print(f"   - Regiões processadas: {data.get('regions_processed', 0)}")
                print(f"   - Imagens baixadas: {data.get('images_downloaded', 0)}")
                
                # Decodificar ZIP do base64
                zip_data = base64.b64decode(data["file_base64"])
                
                # Abrir ZIP na memória
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    file_list = zf.namelist()
                    print(f"\n📦 Arquivos no ZIP:")
                    for filename in file_list:
                        print(f"   - {filename}")
                    
                    # Verificar imagens PNG
                    png_files = [f for f in file_list if f.startswith("crop_region") and f.endswith(".png")]
                    
                    if png_files:
                        print(f"\n🔍 Verificando propriedades das imagens PNG:")
                        for png_file in png_files:
                            with zf.open(png_file) as img_file:
                                img = Image.open(img_file)
                                print(f"\n   📸 {png_file}:")
                                print(f"      - Formato: {img.format}")
                                print(f"      - Modo: {img.mode}")
                                print(f"      - Tamanho: {img.size}")
                                print(f"      - Tem canal alfa: {'Sim' if img.mode in ('RGBA', 'LA') else 'Não'}")
                                
                                # Verificar se tem fundo branco
                                if img.mode == 'RGBA':
                                    # Pegar alguns pixels de exemplo para verificar
                                    pixels = []
                                    for x in range(0, min(10, img.width)):
                                        for y in range(0, min(10, img.height)):
                                            pixels.append(img.getpixel((x, y)))
                                    
                                    # Verificar se há pixels com fundo branco (255, 255, 255, 255)
                                    has_white = any(p == (255, 255, 255, 255) for p in pixels)
                                    print(f"      - Detectado fundo branco: {'Sim' if has_white else 'Verificar manualmente'}")
                    else:
                        print("⚠️  Nenhuma imagem PNG de crop encontrada no ZIP")
                
                print("\n✅ Teste concluído com sucesso!")
            else:
                print(f"❌ Erro no processamento: {data.get('error', 'Erro desconhecido')}")
                
        elif response.status_code == 400:
            print(f"❌ Requisição inválida: {response.json().get('error', 'Erro desconhecido')}")
        else:
            print(f"❌ Erro HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar à API. Certifique-se de que está rodando em http://localhost:8877")
        print("   Execute: python app.py")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        
    print("\n" + "=" * 60)

if __name__ == "__main__":
    # Verificar se foi passada uma URL SVG como argumento
    if len(sys.argv) > 1:
        test_svg_url = sys.argv[1]
        print(f"Usando SVG URL fornecida: {test_svg_url}")
    
    test_svg_crop_api()