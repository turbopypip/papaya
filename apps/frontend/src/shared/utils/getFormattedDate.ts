import {format} from 'date-fns';

export default function getFormattedDate(dateString) {
  // Парсим строку даты
  const date = new Date(dateString);

  // Форматируем дату в нужный формат: DD.MM.YYYY : HH.MM
  return format(date, 'dd.MM.yyyy : HH.mm');
}
