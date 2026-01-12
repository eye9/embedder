#!/usr/bin/env python3
"""
Analyze processing results for GUOO-Manifest file
"""

import pandas as pd
from pathlib import Path
import glob

def main():
    # Найдем последний созданный файл результатов
    result_files = glob.glob('temp_files/*/processed_GUOO-Manifest--777Bags.xlsx')
    if result_files:
        latest_file = max(result_files, key=lambda x: Path(x).stat().st_mtime)
        print(f'📄 Анализируем результаты: {latest_file}')
        
        df = pd.read_excel(latest_file)
        
        # Найдем записи с новыми TNVED кодами
        new_codes = df[df['TNVED_Code'].notna() & (df['TNVED_Code'] != '')]
        
        print(f'\n✅ Найдено {len(new_codes)} записей с назначенными TNVED кодами:')
        print('=' * 80)
        
        for idx, row in new_codes.iterrows():
            print(f'\n🔍 Запись {idx + 1}:')
            print(f'   Описание: {str(row["Product Description"])[:100]}...')
            
            url_col = "Link to customer's web-page with item description"
            url = str(row.get(url_col, ""))
            print(f'   URL: {url[:80]}...')
            
            print(f'   TNVED код: {row["TNVED_Code"]}')
            print(f'   Причина: {str(row["Selection_Reason"])[:150]}...')
            
            # Проверим оригинальный HTS Code
            original_hts = row.get('HTS Code', '')
            if pd.isna(original_hts) or original_hts == '':
                print(f'   ✅ Код успешно назначен (был пустой)')
            else:
                print(f'   ⚠️ Оригинальный HTS Code: {original_hts}')
        
        print(f'\n📊 Сводка результатов:')
        print(f'   • Всего записей в файле: {len(df)}')
        print(f'   • Записей с назначенными кодами: {len(new_codes)}')
        
        # Подсчет типов совпадений
        url_matches = len([r for r in new_codes["Selection_Reason"] if "Found by URL" in str(r)])
        semantic_matches = len([r for r in new_codes["Selection_Reason"] if "semantic search" in str(r)])
        
        print(f'   • URL совпадений: {url_matches}')
        print(f'   • Семантических совпадений: {semantic_matches}')
        
        # Показать качество семантических совпадений
        if semantic_matches > 0:
            print(f'\n🎯 Детали семантических совпадений:')
            for idx, row in new_codes.iterrows():
                reason = str(row["Selection_Reason"])
                if "semantic search" in reason and "Similarity Score:" in reason:
                    # Извлечь similarity score
                    import re
                    score_match = re.search(r'Similarity Score: ([\d.]+)', reason)
                    if score_match:
                        score = float(score_match.group(1))
                        quality = "🟢 Высокое" if score > 0.5 else "🟡 Среднее" if score > 0.3 else "🔴 Низкое"
                        print(f'   • Запись {idx + 1}: {score:.3f} {quality}')
        
    else:
        print('❌ Файлы результатов не найдены')

if __name__ == "__main__":
    main()