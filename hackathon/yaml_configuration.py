from collections import Counter
from collections import UserDict
from typing import Counter #Drop once put on webapp and use python >=3.9

class YAMLConfiguration(UserDict):
    # Note Dict[str, Union[str, List]]

    def __init__(self, *arg, **kw) -> None:
        super(YAMLConfiguration, self).__init__(*arg, **kw)

    def get_row_counter(self) -> Counter[int]:
        '''Returns a counter counting the number of visuals in each row'''
        if self:
            return Counter([row["Row"] for row in self["Rows"]])
        else:
            return Counter()

    def update_configuration(self, new_row_list: Counter[int]) -> None:
        '''Modifies configuration by removing and adding visuals to align to new_row_list.'''
        current_row_list = self.get_row_counter()
        if new_row_list != current_row_list:
            new_row_list.subtract(current_row_list)
            for row, change in new_row_list.items():
                if change > 0:
                    self._add_to_configuration(row, change)
                elif change < 0:
                    self._remove_from_configuration(row, -change)
    

    def _remove_from_configuration(self, row_num: int, N: int) -> None:
        '''Modifies configuration by removing the last N visuals from row number row_num.'''
        new_position = 0
        for position, record in enumerate(reversed(self["Rows"])):
            if record['Row'] == row_num:
                new_position = len(self["Rows"]) - position
                break
        for i in range(N):
            self["Rows"].pop(new_position - i - 1)


    def _add_to_configuration(self, row_num: int, times: int) -> None:
        '''Modifies configuration by adding N blank visuals to row number row_num.'''
        new_position = 0
        for position, record in enumerate(self["Rows"]):
            if record['Row'] > row_num:
                break
            new_position = position + 1
        blank_record_config = {'Row': row_num, 'chartType': 'unconfigured', 'Title': 'Please Configure Visual', 'Subtitle': '', 'Note': '', 'Unit': None, 'unitLoc': None, 'Decimals': None, 'LabelsYN': None, 'legendConcept': None, 'legendLoc': None, 'xAxisConcept': None, 'yAxisConcept': None, 'downloadYN': None, 'dataLink': None, 'metadataLink': None, 'DATA': None}
        for _ in range(times):
            self["Rows"].insert(new_position, blank_record_config)