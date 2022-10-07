import './app.css'
import App from './App.svelte'

const app = new App({
  target: document.getElementById('app')
})

const parts = document.location.href.split('?');
if(parts.length >= 2) {
  if(parts[1] == 'dark') {
    document.body.classList.add('dark');
  }
}

export default app
