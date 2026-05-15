import {create} from 'zustand';

export const useGlobalStore = create(set => ({
  loading: false,
  selectedDate: '',

  setLoading: loading => set({loading}),
  setSelectedDate: date => set({selectedDate: date}),
}));
