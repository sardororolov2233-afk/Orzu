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

class PresentationState(StatesGroup):
    tema = State()
    muallif = State()
    sahifa = State()
    shablon = State()
    til = State()
    mode = State()
    waiting_for_images = State()
    confirm_images = State()
    confirmation = State()
    
    # Tahrirlash holatlari
    edit_mode = State()
    edit_tema = State()
    edit_muallif = State()

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


