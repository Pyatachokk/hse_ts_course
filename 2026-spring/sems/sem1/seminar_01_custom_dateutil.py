import pandas as pd
from datetime import datetime
from enum import Enum
from operator import itemgetter
from typing import Iterable
from pandas.tseries.frequencies import to_offset

class DateError(Exception):
    """
    Исключение, вызываемое при несоответствии дат указанной частоте.
    """
    pass


class Offset:
    """
    Вспомогательный класс, описывающий смещение (delta) и правила частоты (conversion_rule).
    """
    def __init__(
        self,
        delta: pd.DateOffset | None,
        conversion_rule: str | None,
    ):
        self.delta = delta
        self.conversion_rule = conversion_rule

    def get_rule_obj(self) -> pd.DateOffset:
        """
        Возвращает объект с правилом частоты (DateOffset).
        """
        if self.conversion_rule is None:
            raise ValueError("Нельзя получить правило из нерегулярной серии.")
        try:
            return to_offset(self.conversion_rule)
        except ValueError:
            raise NotImplementedError(
                f"Данная частота {self.conversion_rule} не поддерживается."
            )


class Frequency(Enum):
    """
    Перечисление частот, каждая из которых содержит:
    - Offset (delta + conversion_rule)
    - Методы для проверки и выравнивания дат
    """

    IRREGULAR = Offset(delta=None, conversion_rule=None)
    D         = Offset(delta=pd.DateOffset(days=1),  conversion_rule="D")
    W_MON     = Offset(delta=pd.DateOffset(weeks=1), conversion_rule="W-MON")
    W_TUE     = Offset(delta=pd.DateOffset(weeks=1), conversion_rule="W-TUE")

    def align_dates(self, dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
        """
        Выравнивает (пригоняет) переданный DatetimeIndex под требуемую частоту.
        Для W_XXX пытается сдвинуть даты в разумном диапазоне (±4 дня),
        если даты не попадают точно на нужную частоту.
        """
        # Для демонстрации оставим базовую проверку на тип
        if not isinstance(dates, pd.DatetimeIndex):
            raise TypeError(f"Ожидается pd.DatetimeIndex, получен {type(dates)}.")

        match self:
            case Frequency.IRREGULAR | Frequency.D:
                # Для дневной (D) и нерегулярной (IRREGULAR) частоты
                # возвращаем даты без изменений
                return dates

            case _:
                # Для недельной частоты
                try:
                    self.ensure(dates, check_deltas=True)
                    return dates
                except DateError:
                    date_range = pd.date_range(
                        dates.min() - pd.DateOffset(months=1),
                        dates.max() + pd.DateOffset(months=1),
                        freq=self.value.conversion_rule,
                    )

                    result = pd.Series(pd.NA, index=dates)

                    # Попытка найти смещение от -4 до +4 дней
                    for i in [0, -1, 1, -2, 2, -3, 3, -4, 4]:
                        if dates.empty:
                            break

                        shifted_dates = dates + pd.offsets.Day(n=i)
                        shifted_data = pd.DataFrame({"origin_date": dates}, index=shifted_dates)
                        date_intersection = shifted_data.index.intersection(date_range)

                        origin_dates = shifted_data.loc[
                            date_intersection, "origin_date"
                        ].values

                        result.loc[origin_dates] = date_intersection
                        # Обновим "пустые" даты и сам диапазон
                        dates = result.loc[result.isna()].index
                        date_range = date_range.difference(date_intersection)

                    if not dates.empty or result.isna().any():
                        raise DateError(
                            f"Не удалось сконвертировать некоторые даты: {dates.to_list()}\n\n{result}"
                        )

                    return pd.DatetimeIndex(result.values)

    def ensure(
        self,
        array: Iterable[datetime],
        target_array: Iterable[datetime] | None = None,
        check_deltas=False,
    ) -> None:
        """
        Проверяет, что все даты в array попадают на нужную частоту.
        Если target_array не None, длины массивов должны совпадать.
        При check_deltas=True проверяется, что разность между соседними датами
        (или датами из array и target_array) согласована с частотой.
        """
        if target_array is not None:
            assert len(array) == len(target_array), "Длины массивов должны совпадать."

        if self == Frequency.IRREGULAR:
            raise DateError("Частота IRREGULAR не поддерживает проверку ensure.")

        # Проверка, что каждая дата действительно "лежит" на шаге нашей частоты
        rule_object = self.value.get_rule_obj()
        is_not_correct = [
            i for i, date in enumerate(array) if not rule_object.is_on_offset(date)
        ]
        if is_not_correct:
            incorrect_dates = (
                itemgetter(*is_not_correct)(array)
                if len(is_not_correct) > 1
                else [array[is_not_correct[0]]]
            )
            incorrect_dates_str = ", \n".join(
                [date.strftime("%Y-%m-%d") for date in incorrect_dates]
            )
            raise DateError(
                f"Обнаружены даты, которые не соответствуют частоте {self.name}:\n{incorrect_dates_str}"
            )

        # Проверка дельт
        if check_deltas:
            start_index = 1 if target_array is None else 0
            for i in range(start_index, len(array)):
                source_date = array[i - 1] if target_array is None else array[i]
                target_date = array[i]     if target_array is None else target_array[i]
                if source_date == target_date:
                    raise DateError(f"Дублированная дата: {target_date}")

                ok = False
                updated_date = source_date
                while updated_date <= target_date:
                    updated_date += self.value.delta
                    if updated_date == target_date:
                        ok = True
                        break
                if not ok:
                    raise DateError(
                        f"Даты не согласованы с частотой {self.name}: {source_date}, {target_date}"
                    )

    def get_ensure_percentage(self, array: Iterable[datetime], check_deltas=False) -> float:
        """
        Возвращает долю подряд идущих пар дат, которые согласованы с данной частотой.
        """
        num_pairs = len(array) - 1
        if num_pairs <= 0:
            return 1.0  # Если всего одна дата или нет дат, условно считаем 100%

        num_valid = 0
        for i in range(num_pairs):
            pair = [array[i], array[i + 1]]
            try:
                self.ensure(pair, check_deltas=check_deltas)
                num_valid += 1
            except DateError:
                pass

        return num_valid / num_pairs

    def get_denominator_percentage(
        self, array: Iterable[datetime], day_delta: int
    ) -> float:
        """
        Возвращает долю пар дат (из подряд идущих), разность между которыми 
        кратна day_delta дням.
        """
        num_pairs = len(array) - 1
        if num_pairs <= 0:
            return 1.0

        num_valid = 0
        for i in range(num_pairs):
            if not (array[i + 1] - array[i]).days % day_delta:
                num_valid += 1

        return num_valid / num_pairs
