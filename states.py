from aiogram.fsm.state import State, StatesGroup

class ReferatState(StatesGroup):
    tema = State()
    ish_turi = State()
    sahifa = State()
    uslub = State()
    universitet = State()
    fakultet = State()
    muallif = State()
    kurs_guruh = State()
    til = State()
    confirmation = State()
    tariff_selection = State()
    waiting_for_plan_approval = State()
    # Edit mode states
    edit_mode = State()


class CourseWorkState(StatesGroup):
    tema = State()
    sahifa = State()
    uslub = State()
    universitet = State()
    fakultet = State()
    muallif = State()
    kurs = State()
    guruh = State()
    til = State()
    confirmation = State()
    tariff_selection = State()
    waiting_for_plan_approval = State()
    # Edit mode states
    edit_mode = State()


