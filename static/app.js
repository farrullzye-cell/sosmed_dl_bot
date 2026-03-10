(function(){
  // burger
  document.addEventListener('click', function(e){
    const burger = e.target.closest('.navbar-burger');
    if(!burger) return;
    const targetId = burger.dataset.target;
    const menu = document.getElementById(targetId);
    burger.classList.toggle('is-active');
    if(menu) menu.classList.toggle('is-active');
  });

  // theme
  const root = document.documentElement;
  const btn = document.getElementById('themeToggle');
  const saved = localStorage.getItem('theme');
  if(saved === 'dark') root.setAttribute('data-theme','dark');

  function renderBtn(){
    if(!btn) return;
    const isDark = root.getAttribute('data-theme') === 'dark';
    btn.textContent = isDark ? 'Light Mode' : 'Dark Mode';
  }
  renderBtn();

  if(btn){
    btn.addEventListener('click', function(){
      const isDark = root.getAttribute('data-theme') === 'dark';
      if(isDark){
        root.removeAttribute('data-theme');
        localStorage.setItem('theme','light');
      }else{
        root.setAttribute('data-theme','dark');
        localStorage.setItem('theme','dark');
      }
      renderBtn();
    });
  }
})();
