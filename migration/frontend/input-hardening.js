(function(){
  'use strict';

  function setAttrs(el, attrs){
    Object.entries(attrs).forEach(function(entry){
      var k=entry[0], v=entry[1];
      if(v===null) el.removeAttribute(k);
      else el.setAttribute(k,v);
    });
  }

  function hardenInputs(root){
    root=root||document;

    var uemail=root.querySelector&&root.querySelector('#uemail');
    if(uemail){
      uemail.removeAttribute('readonly');
      uemail.removeAttribute('onfocus');
      setAttrs(uemail,{type:'email',inputmode:'email',autocomplete:'new-password',autocapitalize:'none',spellcheck:'false'});
    }
    var upass=root.querySelector&&root.querySelector('#upass');
    if(upass){
      upass.removeAttribute('readonly');
      upass.removeAttribute('onfocus');
      setAttrs(upass,{type:'password',inputmode:'text',autocomplete:'new-password'});
    }

    var ids={
      email:{type:'email',inputmode:'email',autocomplete:'email',autocapitalize:'none',spellcheck:'false'},
      pass:{type:'password',inputmode:'text',autocomplete:'current-password'},
      ownerName:{type:'text',inputmode:'text',autocomplete:'name'},
      ownerEmail:{type:'email',inputmode:'email',autocomplete:'email',autocapitalize:'none',spellcheck:'false'},
      ownerPass:{type:'password',inputmode:'text',autocomplete:'new-password'},
      uname:{type:'text',inputmode:'text',autocomplete:'name'},
      mname:{type:'text',inputmode:'text',autocomplete:'name'},
      mphone:{type:'tel',inputmode:'tel',autocomplete:'tel'},
      mmenu:{type:'text',inputmode:'text',autocomplete:'off'},
      iname:{type:'text',inputmode:'text',autocomplete:'off'},
      iqty:{inputmode:'decimal'},
      iunit:{type:'text',inputmode:'text',autocomplete:'off'},
      imin:{inputmode:'decimal'},
      etitle:{type:'text',inputmode:'text',autocomplete:'off'},
      eamount:{inputmode:'decimal'},
      ecat:{type:'text',inputmode:'text',autocomplete:'off'},
      carryAmount:{inputmode:'decimal'},
      pphone:{type:'tel',inputmode:'tel',autocomplete:'tel'},
      pplan:{inputmode:'decimal'},
      ppaid:{inputmode:'decimal'},
      mealAlertAdminPhone:{type:'tel',inputmode:'tel',autocomplete:'tel'},
      mealAlertAdminEmail:{type:'email',inputmode:'email',autocomplete:'email',autocapitalize:'none',spellcheck:'false'},
      mealAlertChefPhone:{type:'tel',inputmode:'tel',autocomplete:'tel'},
      mealAlertChefEmail:{type:'email',inputmode:'email',autocomplete:'email',autocapitalize:'none',spellcheck:'false'}
    };

    Object.keys(ids).forEach(function(id){
      var el=root.querySelector&&root.querySelector('#'+id);
      if(el && !el.readOnly && !el.disabled) setAttrs(el,ids[id]);
    });

    var searches=[
      ['memberSearch','Search members…'],
      ['inventorySearch','Search items…'],
      ['expenseSearch','Search expense, category, amount or date…']
    ];
    searches.forEach(function(item){
      var id=item[0], ph=item[1];
      var el=(root.querySelector&&root.querySelector('#'+id)) ||
             (root.querySelector&&root.querySelector('input[placeholder="'+ph+'"]'));
      if(el){
        if(!el.id) el.id=id;
        setAttrs(el,{type:'search',inputmode:'search',enterkeyhint:'search',autocomplete:'off',autocapitalize:'none',spellcheck:'false'});
      }
    });

    if(root.querySelectorAll){
      root.querySelectorAll('input[type="number"]:not([readonly]):not([disabled])').forEach(function(el){
        el.setAttribute('inputmode','decimal');
      });
      root.querySelectorAll('input:not([type]),input[type="text"]').forEach(function(el){
        if(!el.readOnly && !el.disabled && !el.getAttribute('inputmode')) el.setAttribute('inputmode','text');
      });
    }
  }

  function textFilter(selector, value){
    var q=String(value||'').trim().toLowerCase();
    document.querySelectorAll(selector).forEach(function(row){
      row.style.display=(!q || String(row.textContent||'').toLowerCase().indexOf(q)>=0)?'':'none';
    });
  }

  function installSearchFixes(){
    if(typeof window.setMemberView==='function' && !window.setMemberView.__a2TypingSafe){
      var oldMember=window.setMemberView;
      var member=function(k,v){
        window._memberView=Object.assign({},window._memberView||{},((function(){var o={};o[k]=v;return o})()));
        if(k==='q'){ textFilter('.main .card.list .row',v); return; }
        return oldMember(k,v);
      };
      member.__a2TypingSafe=true;
      window.setMemberView=member;
    }

    if(typeof window.setInventoryView==='function' && !window.setInventoryView.__a2TypingSafe){
      var oldInventory=window.setInventoryView;
      var inventory=function(k,v){
        window._inventoryView=Object.assign({},window._inventoryView||{},((function(){var o={};o[k]=v;return o})()));
        if(k==='q'){ textFilter('.main .card.list .row',v); return; }
        return oldInventory(k,v);
      };
      inventory.__a2TypingSafe=true;
      window.setInventoryView=inventory;
    }

    if(typeof window.setExpenseView==='function' && !window.setExpenseView.__a2TypingSafe){
      var oldExpense=window.setExpenseView;
      var expense=function(k,v){
        window._expenseView=Object.assign({},window._expenseView||{},((function(){var o={};o[k]=v;return o})()));
        if(k==='q'){
          var selector=document.querySelector('.expense-row')?'.expense-row':'.main .card.list .row';
          textFilter(selector,v);
          return;
        }
        return oldExpense(k,v);
      };
      expense.__a2TypingSafe=true;
      window.setExpenseView=expense;
    }
  }

  function injectStyle(){
    if(document.getElementById('a2-input-hardening-style')) return;
    var style=document.createElement('style');
    style.id='a2-input-hardening-style';
    style.textContent='input:not([type=hidden]):not([type=file]),select,textarea{min-height:44px;touch-action:manipulation;caret-color:#59f3b0} .ref-search{min-height:46px} @media(max-width:900px){input:not([type=hidden]):not([type=file]),select,textarea{font-size:16px!important}}';
    document.head.appendChild(style);
  }

  function boot(){
    injectStyle();
    hardenInputs(document);
    installSearchFixes();
  }

  document.addEventListener('DOMContentLoaded',boot);
  window.addEventListener('load',boot);
  var observer=new MutationObserver(function(mutations){
    mutations.forEach(function(m){
      m.addedNodes.forEach(function(node){
        if(node.nodeType===1) hardenInputs(node);
      });
    });
    installSearchFixes();
  });
  observer.observe(document.documentElement,{childList:true,subtree:true});
  setInterval(installSearchFixes,1000);
})();
