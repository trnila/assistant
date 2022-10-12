import './app.css'
import App from './App.svelte'

const app = new App({
  target: document.getElementById('app')
})

const parts = document.location.href.split('?');
if ((parts.length >= 2 && parts[1] == 'dark') || localStorage.getItem('darkmode') === '1') {
  document.body.classList.add('dark');
}

export default app
