import './app.css'
import App from './App.svelte'
import { mount } from "svelte";

const app = mount(App, {
  target: document.getElementById('app')
})

const parts = document.location.href.split('?');
const dark_url = (parts.length >= 2 && parts[1] == 'dark');
const dark_browser = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
const dark_user = localStorage.getItem('darkmode') === '1';

if (localStorage.getItem('darkmode') !== '0' && (dark_user || dark_browser || dark_url)) {
  document.body.classList.add('dark');
}

export default app
