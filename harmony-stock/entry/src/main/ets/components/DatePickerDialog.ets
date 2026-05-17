@Component
export struct DatePickerDialog {
  @Link selectedDate: string;
  @Link tradingDays: string[];
  @Prop currentDate: string = '';
  @Prop visible: boolean = false;
  private onConfirm?: (date: string) => void;
  private onCancel?: () => void;
  
  @State currentYear: number = 2024;
  @State currentMonth: number = 1;
  @State tempSelectedDate: string = '';

  aboutToAppear() {
    if (this.currentDate) {
      this.tempSelectedDate = this.currentDate;
      this.currentYear = parseInt(this.currentDate.substring(0, 4));
      this.currentMonth = parseInt(this.currentDate.substring(4, 6));
    }
  }

  getDaysInMonth(year: number, month: number): number {
    return new Date(year, month, 0).getDate();
  }

  getFirstDayOfMonth(year: number, month: number): number {
    return new Date(year, month - 1, 1).getDay();
  }

  formatDate(year: number, month: number, day: number): string {
    let monthStr = month < 10 ? `0${month}` : `${month}`;
    let dayStr = day < 10 ? `0${day}` : `${day}`;
    return `${year}${monthStr}${dayStr}`;
  }

  isTradingDay(dateStr: string): boolean {
    return this.tradingDays.includes(dateStr);
  }

  getCalendarDays(): number[] {
    let daysInMonth = this.getDaysInMonth(this.currentYear, this.currentMonth);
    let firstDay = this.getFirstDayOfMonth(this.currentYear, this.currentMonth);
    let totalCells = daysInMonth + firstDay;
    let result: number[] = [];
    for (let i = 0; i < totalCells; i++) {
      result.push(i);
    }
    return result;
  }

  getFirstDay(): number {
    return this.getFirstDayOfMonth(this.currentYear, this.currentMonth);
  }

  getDayFromIndex(index: number): number {
    return index - this.getFirstDay() + 1;
  }

  getDateStrFromIndex(index: number): string {
    let day = this.getDayFromIndex(index);
    return this.formatDate(this.currentYear, this.currentMonth, day);
  }

  isDaySelected(index: number): boolean {
    return this.tempSelectedDate === this.getDateStrFromIndex(index);
  }

  handlePrevMonth() {
    if (this.currentMonth === 1) {
      this.currentYear--;
      this.currentMonth = 12;
    } else {
      this.currentMonth--;
    }
  }

  handleNextMonth() {
    if (this.currentMonth === 12) {
      this.currentYear++;
      this.currentMonth = 1;
    } else {
      this.currentMonth++;
    }
  }

  handleDateClick(day: number) {
    let dateStr = this.formatDate(this.currentYear, this.currentMonth, day);
    if (this.isTradingDay(dateStr)) {
      this.tempSelectedDate = dateStr;
    }
  }

  handleConfirm() {
    if (this.tempSelectedDate && this.onConfirm) {
      this.onConfirm(this.tempSelectedDate);
    }
  }

  @Builder
  CalendarGrid() {
    Column() {
      Row() {
        ForEach(['日', '一', '二', '三', '四', '五', '六'], (day: string) => {
          Text(day)
            .width('14.28%')
            .textAlign(TextAlign.Center)
            .fontSize(10)
            .fontColor('#8c8c8c')
            .padding({ top: 6, bottom: 6 })
        })
      }
      .width('100%')

      Grid() {
        ForEach(this.getCalendarDays(), (index: number) => {
          GridItem() {
            if (index < this.getFirstDay()) {
              Text('')
                .width(32)
                .height(32)
            } else {
              Text(this.getDayFromIndex(index).toString())
                .width(32)
                .height(32)
                .textAlign(TextAlign.Center)
                .fontSize(12)
                .fontColor(this.isDaySelected(index) ? Color.White : (this.isTradingDay(this.getDateStrFromIndex(index)) ? '#262626' : '#d9d9d9'))
                .backgroundColor(this.isDaySelected(index) ? '#1890ff' : Color.Transparent)
                .borderRadius(16)
                .onClick(() => this.handleDateClick(this.getDayFromIndex(index)))
            }
          }
        })
      }
      .columnsTemplate('1fr 1fr 1fr 1fr 1fr 1fr 1fr')
      .rowsGap(2)
      .columnsGap(2)
      .width('100%')
      .height(200)
    }
    .width('100%')
  }

  build() {
    Column() {
      Row() {
        Button('<')
          .fontSize(14)
          .width(32)
          .height(32)
          .backgroundColor(Color.Transparent)
          .onClick(() => this.handlePrevMonth())

        Text(`${this.currentYear}年${this.currentMonth}月`)
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .layoutWeight(1)
          .textAlign(TextAlign.Center)

        Button('>')
          .fontSize(14)
          .width(32)
          .height(32)
          .backgroundColor(Color.Transparent)
          .onClick(() => this.handleNextMonth())
      }
      .width('100%')
      .padding({ left: 8, right: 8, top: 8, bottom: 8 })

      Divider()

      this.CalendarGrid()

      Divider()

      Row() {
        Button('取消')
          .width('45%')
          .height(32)
          .backgroundColor('#F5F5F5')
          .fontColor('#666666')
          .onClick(() => {
            if (this.onCancel) {
              this.onCancel();
            }
          })

        Button('确定')
          .width('45%')
          .height(32)
          .type(ButtonType.Capsule)
          .onClick(() => this.handleConfirm())
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceAround)
      .padding(12)
    }
    .width('100%')
    .backgroundColor(Color.White)
    .borderRadius({ topLeft: 12, topRight: 12 })
  }
}
