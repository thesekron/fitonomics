# Meals JSON Format Guide

## Новый формат JSON для meals

### Структура файла
```json
{
  "budget_low": [...],
  "budget_mid": [...],
  "budget_high": [...]
}
```

### Формат каждого блюда
```json
{
  "id": "ow_breakfast_1",           // Формат: ow_{category}_{number}
  "pack_number": 1,                 // Номер пакета (1-10)
  "category": "breakfast",          // breakfast, lunch, dinner
  "name_en": "Oat & Egg Boost+",    // Английское название
  "name_ru": "Овсянка с Яйцом+",    // Русское название
  "name_uz": "Tuxumli Suli Yormasi+", // Узбекское название
  "text_en": "...",                 // Английское описание
  "text_ru": "...",                 // Русское описание
  "text_uz": "...",                 // Узбекское описание
  "image": "media/meals/budget_low/breakfast/1.png" // Путь к изображению
}
```

### ID Формат
- **Breakfast**: `ow_breakfast_1`, `ow_breakfast_2`, ...
- **Lunch**: `ow_lunch_1`, `ow_lunch_2`, ... (или `low_lunch_1` для совместимости)
- **Dinner**: `ow_dinner_1`, `ow_dinner_2`, ... (или `low_dinner_1` для совместимости)

### Структура папок media
```
media/meals/
├── budget_low/
│   ├── breakfast/
│   ├── lunch/
│   └── dinner/
├── budget_mid/
│   ├── breakfast/
│   ├── lunch/
│   └── dinner/
└── budget_high/
    ├── breakfast/
    ├── lunch/
    └── dinner/
```

### Категории блюд
- **breakfast** - Завтрак
- **lunch** - Обед  
- **dinner** - Ужин

### Бюджеты
- **budget_low** - Низкий бюджет
- **budget_mid** - Средний бюджет
- **budget_high** - Высокий бюджет

### Особенности
- Все названия переводятся на 3 языка: EN, RU, UZ
- Описания содержат эмодзи, ингредиенты, цену, калории
- Изображения хранятся в соответствующих папках по бюджету и категории
- ID содержит префикс категории для лучшей организации
