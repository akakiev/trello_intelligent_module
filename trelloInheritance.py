from trello import TrelloClient
from trello import Board
from trello import Card
from trello import Organization
import numpy as np
import pandas as pd
from trello.customfield import CustomFieldText, CustomFieldCheckbox, \
    CustomFieldNumber, CustomFieldDate, CustomFieldList
from datetime import datetime

("\n"
 "This program based on py-trello library. It works with all three types of data"
 "in trello (web-based project management application) - boards, lists, cards."
 " The program gets names from all users boards in trello, names and ids from all"
 " cards in trello, full names of first members in all cards, values of such "
 "custom fields as sp and payed from all users cards in trello and creates array by pandas"
 " DataFrame(two-dimensional data structure) with all this data, import it to "
 "excel file by command from pandas library.\n")

class BoardTrello():
    """
    Class  representing a Trello board.Board attributes are stored as normal
    Python attributes; access to all sub - objects, however, is always an API call(Lists, Cards).
    """
    def __init__(self, board):
        assert isinstance(board, Board), "Wrong board type, while expected Board: {}".format(type(board))
        self.board = board

    def cards_from_board(self, listName='Done', defaultlabelName=('Task', 'Bug')):
        """
        Returns array with all trello cards for current name of list in board.
        """
        t = []
        lists = self.board.list_lists()
        names = (l.name for l in lists)
        if listName not in names:
            print(lists)
            listName = input("Fill the name of the List:{}".format(str))
        cards = [l.list_cards() for l in lists if l.name == listName]

        for card in cards:
            for c in card:
                assert (len(c.labels) >= 1), "There are no labels '{}' for card '{}':" \
                                             " http://www.trello.com/c/{}".format(c.labels, c, c.id)
            t.extend(filter(lambda x: x.labels[0].name in defaultlabelName, card))
        return t

    def name_member(self, card):
        """
        Returns list with full names of all members in card by members id or just empty field.
        """
        if len(card.idMembers) == 0:
            return ''

        boardMembers = filter(lambda x: x.id in card.idMembers, self.board.all_members())
        memberNames = [boardMember.full_name for boardMember in boardMembers]
        return memberNames if len(memberNames) != 0 else ''

    def sp_from_board(self):
        """
        Returns list of all values of the sp custom field for board.
        """
        for definition in self.board.get_custom_field_definitions():
            if definition.name == 'SP':
                return sorted(list(map(int, definition.list_options.values())))


class CardTrello():
    """
        Class representing a Trello card. Card attributes are stored on
        the object https://developers.trello.com/advanced-reference/card
    """
    def __init__(self, card):
        assert isinstance(card, Card), "Wrong card type, while expected Card: {}".format(type(card))
        self.card = card

    def get_custom_field_by_name(self, cf_name):
        """
        Returns existing custom field by name or creates a new one.
        """
        for cf in card.customFields:
            if cf.name == cf_name:
                return cf
        cf_class = None
        cf_def_id = None
        for definition in card.board.get_custom_field_definitions():
            if definition.name == cf_name:
                cf_def_id = definition.id
                cf_class = {
                'checkbox': CustomFieldCheckbox,
                'date': CustomFieldDate,
                'list': CustomFieldList,
                'number': CustomFieldNumber,
                'text': CustomFieldText,
            }.get(definition.field_type)
        if cf_class is None:
            return None
        return cf_class(card, 'unknown', cf_def_id, '')

    def __get_CF(self, CF):
        """
        Returns value of the custom field in cards.
        """
        assert (self.get_custom_field_by_name(CF).type is not None), "There is" \
    " problem with customfield '{}' on card '{}'".format(self.get_custom_field_by_name(CF), self.card)
        return self.get_custom_field_by_name(CF).value

    def sp(self):
        """
        Returns value of one of the custom fields in cards by name - sp.
        """
        return int(self.__get_CF('SP'))

    def payed(self):
        """
        Returns value of one of the custom fields in cards by name - paid.
        """
        return False if self.__get_CF('Payed') == '' else True


def asignee_for_card(board, card):
    """
    Returns list with full names of the members of the card if there wasn't such names.
    """
    members = board.get_members()
    print('Asignee: ')
    for i, item in enumerate(members):
        print("{} - {}".format(i, members[i].full_name))
    mm = int(input("Fill the Asignee for '{}' from '{}':".format(card.name, board.name)))
    member = [members[mm].full_name]
    card.add_member(members[mm])
    return member

def sp_for_card(board, card, member):
    """
    Returns value of the SP custom field if assignee forgot to choose this value in the card.
    """
    spBoard = board.sp_from_board()
    print('SP value: ')
    for i, item in enumerate(spBoard):
        print("{} - {}".format(i, item))
    ss = int(input("Fill for '{}' SP field in the card '{}':".format(member, card.name)))
    for i, item in enumerate(spBoard):
        spCard = item
        card.get_custom_field_by_name('SP').value = str(spBoard[ss])
        return spCard


array = pd.DataFrame(np.object, index=[], columns=[])
aggregation = pd.DataFrame(np.object, index=[], columns=[])
table = pd.DataFrame(np.object, index=[], columns=[])

# retrieve api key and token
with open('private_key.json') as f:
    pk = json.load(f)
client = TrelloClient(api_key=pk["api_key"], token=pk["token"])
organizations = client.list_organizations()

for org in organizations:
    if org.name == 'rnd':
        break
else:
    print('There is no organization with the specified name')

for board in Organization.get_boards(org, 'open'):
    defNames = [definition.name for definition in board.get_custom_field_definitions()]
    if 'SP' not in defNames: continue

    trelloBoard = BoardTrello(board)
    allCards = trelloBoard.cards_from_board()
    spBoard = trelloBoard.sp_from_board()
    for card in allCards:
        trelloCard = CardTrello(card)
        spCard = trelloCard.sp()
        member = trelloBoard.name_member(card)
        if member == '':
            member = asignee_for_card(board, card)
        if spCard == 0:
            spCard = sp_for_card(board, card, member)
        payed = trelloCard.payed()
        if not payed:
            for m in member:
                link = "http://www.trello.com/c/{}".format(card.id)
                array = array.append({'Project': board.name, 'Summary': card.name,
                                      'Key': card.id, 'Assignee': m, 'Points': spCard, 'URL': link},
                                     ignore_index=True)
if len(array) == 0:
    print("All cards are payed. Nothing to do. Exiting...")
    raise SystemExit()



table = pd.read_excel('ProjectCostUCP.xlsx', 'Лист1')
print("=== Prices ===")
print(table)

aggregation = array[['Project', 'Assignee', 'Points']].groupby(['Assignee', 'Project']).sum().reset_index()
aggregation = aggregation.merge(table, on='Project')
aggregation['Value'] = aggregation.Points * aggregation.Price

writer = pd.ExcelWriter('Salary-Trello-%d.'% datetime.now().year + '%d.xlsx'% datetime.now().month)

array.to_excel(writer, "sp-raw")
aggregation.to_excel(writer, "SP")

writer.save()

print("=== sp-raw ===")
print(array)
print("=== SP ===")
print(aggregation)
print("Result in file: {}".format('Salary-Trello-%d.'% datetime.now().year + '%d.xlsx'% datetime.now().month))
